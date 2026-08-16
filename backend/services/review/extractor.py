"""
Turning a finished lesson into concepts and review questions.

Pure functions over an injected LLM callable, matching
services/lesson/generator.py: no database, no Celery, no API key needed to
test any of the parsing or normalising below.

Reading the lesson's own rendered content - the slide text the student saw
and the narration they heard - is deliberate. Generating questions from the
original one-line requirement would produce questions about things the
lesson never actually covered, which is worse than no questions: the student
cannot tell whether they forgot it or were never taught it.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from .prompts import (
    CONCEPT_SYSTEM, CONCEPT_USER,
    ITEM_SYSTEM, ITEM_USER,
    GRADE_SYSTEM, GRADE_USER,
)

logger = logging.getLogger(__name__)

# Same signature as the lesson generator's, so a single _make_llm_callable
# in the task layer serves both.
LLMCall = Callable[[str, str, int], Awaitable[str]]

VALID_KINDS = {"recall", "mcq", "problem"}
MAX_CONCEPTS_PER_SCENE = 3
MCQ_OPTION_COUNT = 4


class ReviewGenerationError(RuntimeError):
    pass


# ----------------------------------------------------------------- parsing --

def _repair_json(text: str) -> str:
    """Patch the malformed JSON models actually emit.

    Two failures seen in practice, both from real responses:

      - a trailing comma before a closing brace or bracket
      - a dropped object key, e.g. `{"scene_3", "concepts": [...]}` where
        `"scene_id": ` was simply left out

    The second is repaired by reading the bare string as the value of
    whichever key the sibling objects use. That is a guess, but a
    well-founded one - the alternative is discarding a response that is
    otherwise entirely correct.
    """
    # Trailing commas.
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    # A bare string immediately after `{` is a value whose key went missing.
    text = re.sub(r'(\{\s*)"([^"\n]{1,80})"\s*,', r'\1"scene_id": "\2",', text)
    return text


def _close_truncated(text: str) -> str:
    """Close whatever a cut-off response left open.

    Hitting the token limit mid-object is common and the content up to that
    point is usually fine, so recovering the complete entries beats throwing
    the lot away.
    """
    def _scan(s: str):
        curly = square = 0
        in_string = escaped = False
        for ch in s:
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = not in_string
            elif not in_string:
                if ch == "{":
                    curly += 1
                elif ch == "}":
                    curly -= 1
                elif ch == "[":
                    square += 1
                elif ch == "]":
                    square -= 1
        return curly, square, in_string

    _, _, in_string = _scan(text)
    if in_string:
        text += '"'
    # Drop the dangling partial entry FIRST - counting depth before removing
    # it leaves the tally describing text that no longer exists, and the
    # closers then land in the wrong place.
    text = re.sub(r",\s*\{[^{}]*$", "", text)
    curly, square, _ = _scan(text)
    return text + "]" * max(0, square) + "}" * max(0, curly)


def _extract_json(raw: str) -> Any:
    """Pull JSON out of a model response that may be fenced, prefaced,
    lightly malformed, or cut off."""
    if not raw:
        raise ReviewGenerationError("empty response")
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    start, end = text.find("{"), text.rfind("}")
    candidates = [text]
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])
    if start != -1:
        candidates.append(_close_truncated(text[start:]))

    for candidate in candidates:
        for attempt in (candidate, _repair_json(candidate)):
            try:
                return json.loads(attempt)
            except json.JSONDecodeError as exc:
                last = exc

    raise ReviewGenerationError(f"unparseable JSON: {last}")


_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(value: str) -> str:
    """Slide element content is HTML; questions should be written from text."""
    if not value:
        return ""
    text = _TAG_RE.sub(" ", value)
    text = (text.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))
    return re.sub(r"\s+", " ", text).strip()


def slug_for(name: str) -> str:
    """Normalised key used to spot the same concept written two ways.

    Cheap first pass before the embedding comparison: casing, punctuation,
    accents and a leading article are the majority of duplicates, and none of
    them need a model to notice.
    """
    text = unicodedata.normalize("NFKD", name or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().strip()
    text = re.sub(r"^(the|a|an)\s+", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:300]


# ------------------------------------------------------------ scene reading --

def scene_text(scene: Dict[str, Any]) -> Tuple[str, str]:
    """(slide text, narration) for one scene, both plain text.

    Narration lives in the scene's actions as `speech` entries - the same
    text the TTS voice reads - so this is literally what the student heard.
    """
    slide_parts: List[str] = []
    elements = ((scene.get("slide") or {}).get("elements")) or []
    for el in elements:
        if el.get("type") == "text" and el.get("content"):
            cleaned = strip_html(str(el["content"]))
            if cleaned:
                slide_parts.append(cleaned)

    narration_parts: List[str] = []
    for action in scene.get("actions") or []:
        if action.get("type") == "speech" and action.get("content"):
            narration_parts.append(str(action["content"]).strip())

    return "\n".join(slide_parts), "\n".join(narration_parts)


def scene_is_substantive(scene: Dict[str, Any], min_chars: int = 120) -> bool:
    """Skip title cards and outros - there is nothing there to test."""
    slide, narration = scene_text(scene)
    return len(slide) + len(narration) >= min_chars


# ---------------------------------------------------------------- concepts --

def _normalise_concepts(data: Any) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Tuple[str, str]]]:
    """Validate the concept response into {scene_id: [concept, ...]} + edges."""
    if not isinstance(data, dict):
        raise ReviewGenerationError("concept response was not an object")

    by_scene: Dict[str, List[Dict[str, Any]]] = {}
    for entry in data.get("scenes") or []:
        if not isinstance(entry, dict):
            continue
        scene_id = str(entry.get("scene_id") or "").strip()
        if not scene_id:
            continue
        concepts: List[Dict[str, Any]] = []
        seen: set = set()
        for c in entry.get("concepts") or []:
            if isinstance(c, str):
                c = {"name": c}
            if not isinstance(c, dict):
                continue
            name = str(c.get("name") or "").strip()
            slug = slug_for(name)
            if not slug or slug in seen:
                continue
            seen.add(slug)
            concepts.append({
                "name": name[:300],
                "slug": slug,
                "description": (str(c.get("description") or "").strip() or None),
                "primary": bool(c.get("primary", True)),
            })
            if len(concepts) >= MAX_CONCEPTS_PER_SCENE:
                break
        if concepts:
            by_scene[scene_id] = concepts

    edges: List[Tuple[str, str]] = []
    for pair in data.get("prerequisites") or []:
        if not isinstance(pair, dict):
            continue
        before, after = slug_for(str(pair.get("before") or "")), slug_for(str(pair.get("after") or ""))
        # A concept cannot be its own prerequisite, and an edge to a concept
        # this lesson never mentions is not verifiable.
        if before and after and before != after:
            edges.append((before, after))

    return by_scene, edges


async def extract_concepts(
    llm: LLMCall, lesson_title: str, scenes: List[Dict[str, Any]]
) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Tuple[str, str]]]:
    """Concepts per scene, plus within-lesson prerequisite edges."""
    blocks: List[str] = []
    for scene in scenes:
        if not scene_is_substantive(scene):
            continue
        slide, narration = scene_text(scene)
        blocks.append(
            f"--- {scene.get('id')} | {scene.get('title') or ''}\n"
            f"{slide[:1200]}\n{narration[:1500]}"
        )

    if not blocks:
        return {}, []

    raw = await llm(
        CONCEPT_SYSTEM,
        CONCEPT_USER.format(lesson_title=lesson_title, scenes_block="\n\n".join(blocks)),
        4000,
    )
    return _normalise_concepts(_extract_json(raw))


# ------------------------------------------------------------ review items --

def _normalise_items(data: Any) -> List[Dict[str, Any]]:
    """Validate generated questions, dropping anything unusable.

    Dropping is right rather than repairing: a malformed MCQ with three
    options can be fixed, but a question whose answer is missing cannot be
    marked, and an unmarkable question in a review queue is a dead end the
    student cannot get past.
    """
    if not isinstance(data, dict):
        raise ReviewGenerationError("item response was not an object")

    items: List[Dict[str, Any]] = []
    for entry in data.get("items") or []:
        if not isinstance(entry, dict):
            continue
        prompt = str(entry.get("prompt") or "").strip()
        answer = str(entry.get("answer") or "").strip()
        if not prompt or not answer:
            continue

        kind = str(entry.get("kind") or "recall").lower()
        if kind not in VALID_KINDS:
            kind = "recall"

        rubric: Dict[str, Any] = {}
        if kind == "mcq":
            options = [str(o).strip() for o in (entry.get("options") or []) if str(o).strip()]
            options = list(dict.fromkeys(options))  # de-dupe, keep order
            if len(options) < 2 or answer not in options:
                # Not answerable as multiple choice; it still works as recall.
                kind = "recall"
            else:
                rubric["options"] = options[:MCQ_OPTION_COUNT]
                if answer not in rubric["options"]:
                    rubric["options"][-1] = answer

        must = [str(m).strip() for m in (entry.get("must_include") or []) if str(m).strip()]
        if must:
            rubric["must_include"] = must[:6]

        items.append({
            "kind": kind,
            "prompt": prompt[:2000],
            "answer": answer[:2000],
            "rubric": rubric or None,
        })

    return items


async def generate_items(
    llm: LLMCall,
    lesson_title: str,
    scene: Dict[str, Any],
    concepts: List[str],
    count: int = 3,
) -> List[Dict[str, Any]]:
    """Review questions for one scene."""
    slide, narration = scene_text(scene)
    if not (slide or narration):
        return []

    raw = await llm(
        ITEM_SYSTEM,
        ITEM_USER.format(
            lesson_title=lesson_title,
            scene_title=scene.get("title") or "",
            concepts=", ".join(concepts) or "(none identified)",
            slide_text=slide[:2000],
            narration=narration[:2500],
            count=count,
        ),
        4000,
    )
    return _normalise_items(_extract_json(raw))


# -------------------------------------------------------------------- grade --

def _normalise_grade(data: Any) -> Tuple[int, str]:
    if not isinstance(data, dict):
        raise ReviewGenerationError("grade response was not an object")
    try:
        grade = int(data.get("grade"))
    except (TypeError, ValueError):
        raise ReviewGenerationError("grade was not a number")
    # Clamp rather than reject. A model that answers 0 or 5 has still made a
    # judgement, and refusing it would strand the student mid-review.
    grade = max(1, min(4, grade))
    return grade, str(data.get("feedback") or "").strip()[:1000]


async def grade_response(
    llm: LLMCall, prompt: str, answer: str, must_include: List[str], response: str
) -> Tuple[int, str]:
    """Mark a free-text answer, returning (grade 1-4, feedback)."""
    raw = await llm(
        GRADE_SYSTEM,
        GRADE_USER.format(
            prompt=prompt,
            answer=answer,
            must_include=", ".join(must_include) if must_include else "(none given)",
            response=response,
        ),
        1500,
    )
    return _normalise_grade(_extract_json(raw))


def grade_mcq(selected: str, answer: str) -> Tuple[int, str]:
    """Multiple choice marks itself - no model call, no latency, no cost."""
    if (selected or "").strip() == (answer or "").strip():
        return 3, "Correct."
    return 1, f"Not quite - the answer is: {answer}"
