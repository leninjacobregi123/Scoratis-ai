"""
Quiz generation and scoring.

Reuses the same retrieval and LLM-generation building blocks already proven
in this codebase: `HybridRAGService.multi_level_search` (used by the
`search_knowledge_base` agent tool) for grounding questions in the user's
own documents, and `llm_service.generate` (used throughout video_service.py)
for structured JSON generation from an LLM.
"""
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from llm_service import llm_service
from models import Quiz, QuizQuestion, QuizAttempt
from services.rag_service import get_rag_service

logger = logging.getLogger(__name__)

QUIZ_SYSTEM_PROMPT = (
    "You are an expert tutor writing multiple-choice practice questions. "
    "Output only valid JSON, no commentary, no markdown fences."
)

QUIZ_PROMPT_TEMPLATE = """Write {num_questions} multiple-choice practice questions about "{topic}".

{context_block}

Each question must have exactly 4 options with exactly one correct answer.
Base questions on the reference material above when it's relevant; otherwise use your own knowledge.

Respond with ONLY this JSON shape (no markdown fences):
{{
  "questions": [
    {{
      "question_text": "...",
      "options": ["...", "...", "...", "..."],
      "correct_answer": "<must exactly match one of the options>",
      "explanation": "one sentence explaining why the answer is correct",
      "source_chunk_id": <int or null, matching a [chunk_id] from the reference material if you used it>
    }}
  ]
}}"""


def _strip_markdown_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    return cleaned.strip()


def _iter_balanced_json_objects(text: str):
    """Yield every top-level {...} substring in `text`, tracking brace depth
    and string literals so braces inside quoted strings don't miscount.
    Small local models (confirmed here with quantized qwen3:4b under memory
    pressure) routinely "think out loud" in prose before/around the actual
    JSON despite explicit instructions not to - a strict `json.loads` on the
    raw response fails on that prose, so we scan for embedded objects instead."""
    depth = 0
    start = None
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    yield text[start:i + 1]
                    start = None


def _parse_llm_json(response: str) -> dict:
    """Try a direct parse first (the common case); fall back to scanning for
    embedded JSON objects, preferring the LAST one that both parses and has a
    non-empty "questions" list (models that narrate a draft before a "final"
    answer put the real one last)."""
    cleaned = _strip_markdown_fences(response)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    candidates = list(_iter_balanced_json_objects(cleaned))
    for candidate in reversed(candidates):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if parsed.get("questions"):
            return parsed

    raise ValueError("No parseable JSON object with questions found in LLM response")


async def generate_quiz(
    db: AsyncSession,
    *,
    user_id: int,
    topic: str,
    num_questions: int = 5,
) -> Quiz:
    """Generate and persist a quiz. Falls back to a document-free prompt if
    no relevant chunks are found (a brand-new user with no uploads yet is a
    legitimate case, not an error)."""
    num_questions = max(1, min(num_questions, 15))

    rag_service = get_rag_service()
    chunk_results = []
    try:
        chunk_results = await rag_service.multi_level_search(db, topic, user_id)
    except Exception as e:
        logger.warning(f"Quiz generation: retrieval failed, continuing without context: {e}")

    chunk_by_id = {c.chunk_id: c for c in chunk_results[:8]}
    if chunk_by_id:
        context_lines = [f"Reference material:"]
        for chunk_id, chunk in chunk_by_id.items():
            context_lines.append(f"[chunk_id={chunk_id}] {chunk.content[:600]}")
        context_block = "\n".join(context_lines)
    else:
        context_block = "No reference material available - use your own knowledge."

    prompt = QUIZ_PROMPT_TEMPLATE.format(
        num_questions=num_questions, topic=topic, context_block=context_block
    )

    # Small local reasoning models can spend 2000+ tokens narrating before
    # reaching the actual JSON (confirmed on this stack with quantized
    # qwen3:4b) - give this call extra headroom over the app's normal
    # 2048-token default so it has room to actually finish.
    response = await llm_service.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt=QUIZ_SYSTEM_PROMPT,
        max_tokens=6000,
        disable_thinking=True,
    )

    try:
        parsed = _parse_llm_json(response)
        raw_questions = parsed.get("questions", [])
        if not raw_questions:
            raise ValueError("LLM returned no questions")
    except Exception as e:
        logger.error(f"Quiz generation: failed to parse LLM response: {e}")
        raise ValueError("Failed to generate quiz questions - try again") from e

    document_ids = sorted({c.document_id for c in chunk_by_id.values()}) or None

    quiz = Quiz(user_id=user_id, topic=topic, source_document_ids=document_ids)
    db.add(quiz)
    await db.flush()

    for i, q in enumerate(raw_questions[:num_questions]):
        options = q.get("options") or []
        correct = q.get("correct_answer", "")
        if len(options) < 2 or correct not in options:
            continue
        source_chunk_id = q.get("source_chunk_id")
        if source_chunk_id not in chunk_by_id:
            source_chunk_id = None
        db.add(QuizQuestion(
            quiz_id=quiz.id,
            order_index=i,
            question_text=q.get("question_text", "").strip(),
            options=options,
            correct_answer=correct,
            explanation=q.get("explanation"),
            source_chunk_id=source_chunk_id,
        ))

    await db.flush()
    await db.refresh(quiz, attribute_names=["questions"])

    if not quiz.questions:
        raise ValueError("Generated quiz had no valid questions - try again")

    return quiz


async def submit_quiz_attempt(
    db: AsyncSession,
    *,
    quiz: Quiz,
    user_id: int,
    answers: dict,
) -> QuizAttempt:
    """`answers` maps str(question_id) -> selected option string."""
    total = len(quiz.questions)
    correct_count = 0
    missed_question_ids = []

    for question in quiz.questions:
        selected = answers.get(str(question.id))
        if selected == question.correct_answer:
            correct_count += 1
        else:
            missed_question_ids.append(question.id)

    score = (correct_count / total * 100) if total else 0.0

    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user_id,
        score=score,
        answers={"selections": answers, "missed_question_ids": missed_question_ids},
    )
    db.add(attempt)
    await db.flush()
    return attempt
