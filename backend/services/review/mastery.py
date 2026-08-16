"""
What the learner already knows, in a form lesson generation can use.

The concept layer and the review scheduler between them now hold a real
picture of a student's knowledge. This is the piece that spends it: instead
of generating the same course for someone meeting a subject for the first
time and someone revising it the night before an exam, the outline stage is
told what is already solid and what keeps being forgotten.

Deliberately conservative about what counts as "known". Telling a lesson to
skip something the student has not actually mastered leaves a hole they
cannot see, and a hole is far worse than a few minutes of redundant
revision - so the bar for skipping is high and the bar for reinforcing is
low.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# Mastery at or above this is treated as solid enough to skip teaching from
# scratch. Roughly 30 days of survived stability with no recent lapses.
KNOWN_THRESHOLD = 0.60

# Seen, but not holding. These get reinforced rather than skipped or
# re-taught from nothing.
SHAKY_THRESHOLD = 0.25

# Keep the prompt honest in size: a hundred concept names would crowd out
# the learner's actual request.
MAX_LISTED = 12


def classify(rows: Sequence[Dict]) -> Tuple[List[str], List[str]]:
    """Split mastery rows into (known, shaky) concept names.

    `rows` are dicts with at least `name`, `strength` and `lapse_count` -
    the shape ConceptMastery.to_dict produces once joined to Concept.

    A concept with repeated lapses is never reported as known however high
    its strength has climbed: forgetting something three times means the
    student will forget it again, and that is precisely what should be
    revisited rather than skipped.
    """
    known: List[Tuple[float, str]] = []
    shaky: List[Tuple[float, str]] = []

    for row in rows:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        strength = float(row.get("strength") or 0.0)
        lapses = int(row.get("lapse_count") or 0)
        reviews = int(row.get("review_count") or 0)

        if reviews == 0:
            # Taught but never tested. No evidence either way, so it is not
            # claimed as known and not flagged as weak.
            continue

        if strength >= KNOWN_THRESHOLD and lapses < 3:
            known.append((strength, name))
        elif strength < SHAKY_THRESHOLD or lapses >= 2:
            shaky.append((strength, name))

    known.sort(reverse=True)
    shaky.sort()
    return (
        [n for _, n in known[:MAX_LISTED]],
        [n for _, n in shaky[:MAX_LISTED]],
    )


def build_context(known: Sequence[str], shaky: Sequence[str]) -> str:
    """The block handed to the outline stage, or "" when there is nothing
    useful to say.

    Returning empty rather than "the learner knows nothing" matters: a new
    student's first lesson should read as a normal request, not as one
    carrying a list of deficiencies.
    """
    parts: List[str] = []
    if known:
        parts.append(
            "The learner has already demonstrated they understand: "
            + ", ".join(known)
            + ". Do not teach these from scratch. Reference them as known "
              "ground and build on them."
        )
    if shaky:
        parts.append(
            "The learner has struggled with: "
            + ", ".join(shaky)
            + ". Give these more time and a second angle, not a repeat of the "
              "same explanation."
        )
    return "\n".join(parts)


async def mastery_context_for(session, user_id: int, requirement: str) -> str:
    """Look up this learner's mastery and turn it into prompt context.

    Scoped by relevance to the request rather than dumping the whole graph:
    a calculus lesson has no use for what they know about photosynthesis,
    and an unfiltered list would spend the prompt budget on noise.

    Any failure here returns "" - a lesson generated without personalisation
    is the status quo, and is much better than no lesson at all.
    """
    try:
        from sqlalchemy import select
        from models import ConceptMastery, Concept

        rows = (await session.execute(
            select(ConceptMastery, Concept)
            .join(Concept, Concept.id == ConceptMastery.concept_id)
            .where(
                ConceptMastery.user_id == user_id,
                ConceptMastery.review_count > 0,
            )
        )).all()

        if not rows:
            return ""

        candidates = [{**m.to_dict(), "name": c.name} for m, c in rows]
        relevant = _filter_relevant(
            candidates, requirement, _embeddings_for(candidates, requirement)
        )
        known, shaky = classify(relevant)
        return build_context(known, shaky)

    except Exception as exc:
        logger.warning(f"Could not load mastery context for user {user_id}: {exc}")
        return ""


def mastery_context_sync(db, user_id: int, requirement: str) -> str:
    """Sync twin of mastery_context_for, for the Celery worker.

    Lesson generation runs in a prefork worker on a synchronous session, so
    it cannot await the async lookup. The interesting logic - classify and
    build_context - is shared; only the query differs.
    """
    try:
        from models import ConceptMastery, Concept

        rows = (
            db.query(ConceptMastery, Concept)
            .join(Concept, Concept.id == ConceptMastery.concept_id)
            .filter(
                ConceptMastery.user_id == user_id,
                ConceptMastery.review_count > 0,
            )
            .all()
        )
        if not rows:
            return ""

        candidates = [{**m.to_dict(), "name": c.name} for m, c in rows]
        relevant = _filter_relevant(
            candidates, requirement, _embeddings_for(candidates, requirement)
        )
        known, shaky = classify(relevant)
        return build_context(known, shaky)

    except Exception as exc:
        logger.warning(f"Could not load mastery context for user {user_id}: {exc}")
        return ""


# Cosine similarity between the request and a concept name above which the
# concept counts as relevant to this lesson. Measured on real data: for
# "teach me binary search and how fast it is", the binary search concept
# scores 0.76 and "time complexity O(log n)" 0.26, while every concept from
# an unrelated subject sits below 0.10. 0.20 sits in that gap with room on
# both sides.
RELEVANCE_THRESHOLD = 0.20


def _filter_relevant(
    rows: List[Dict], requirement: str, embeddings: Optional[Dict[str, list]] = None
) -> List[Dict]:
    """Keep concepts plausibly related to what was asked for.

    Word overlap alone is too blunt here. "Teach me binary search and how
    fast it is" shares no word with "time complexity O(log n)", so the
    obviously-relevant concept the student keeps failing got dropped and the
    lesson was personalised as if they had never struggled with it.

    Concept embeddings already exist for deduplication, so relevance reuses
    them: one embed of the request, compared against vectors already stored.
    Word overlap stays as the fallback for when the embedding service is
    unavailable, and anything matching either test is kept.
    """
    words = {w for w in _tokens(requirement) if len(w) > 3}
    by_words = [
        row for row in rows
        if words & {w for w in _tokens(row.get("name", "")) if len(w) > 3}
    ] if words else []

    by_vector: List[Dict] = []
    if embeddings:
        target = embeddings.get("__request__")
        if target:
            for row in rows:
                vec = embeddings.get(row.get("name"))
                if vec and _cosine(target, vec) >= RELEVANCE_THRESHOLD:
                    by_vector.append(row)

    names = set()
    hits: List[Dict] = []
    for row in by_words + by_vector:
        if row.get("name") not in names:
            names.add(row.get("name"))
            hits.append(row)

    if hits:
        return hits
    # Nothing matched. With embeddings that is a real answer - a Renaissance
    # lesson genuinely has nothing to learn from what they know about binary
    # search, and falling back to "everything" here would paste an unrelated
    # subject's concepts into the prompt. Only the word-overlap-only path
    # falls back, where a miss is much more likely to be the filter's fault.
    return [] if embeddings else rows


def _cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def _embeddings_for(rows: List[Dict], requirement: str) -> Optional[Dict[str, list]]:
    """Vectors for the request and every candidate concept name.

    Returns None if the embedding service is unavailable, which drops the
    filter back to word overlap rather than failing the lesson.
    """
    try:
        from services.embedding_service import get_embedding_service
        service = get_embedding_service()
        if not service:
            return None
        out = {"__request__": service.embed_text(requirement)}
        for row in rows:
            name = row.get("name")
            if name and name not in out:
                out[name] = service.embed_text(name)
        return out
    except Exception as exc:
        logger.warning(f"Relevance embeddings unavailable, using word overlap: {exc}")
        return None


def _tokens(text: str) -> set:
    return {t.strip(".,;:()[]").lower() for t in (text or "").split()}
