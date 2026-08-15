"""
Post-lesson processing: tag the scenes with concepts, then write review
questions from what the lesson actually taught.

Runs as its own task on its own queue, deliberately not inline with lesson
generation. Lesson generation already holds the single worker slot for around
ten minutes while Manim renders; adding several more model calls to the end of
that would delay every queued lesson behind it. The cost is a short window
where a finished lesson has no questions yet, which nobody notices, against a
lesson that takes even longer to appear, which everybody does.
"""
import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

from celery_app import celery_app
from tasks.lesson_tasks import SessionLocal, _make_llm_callable
from models import (
    Lesson, LessonStatus, Concept, SceneConcept, ConceptEdge, ConceptMastery,
    ReviewItem, ReviewKind, CONCEPT_MERGE_THRESHOLD,
)
from services.review.extractor import (
    extract_concepts, generate_items, scene_is_substantive, slug_for,
)

logger = logging.getLogger(__name__)

ITEMS_PER_SCENE = 3
# A lesson with thirty scenes would otherwise produce ninety questions in one
# sitting, which is a wall rather than a review queue.
MAX_ITEMS_PER_LESSON = 24


def _embed(text: str) -> Optional[List[float]]:
    """Embed a concept name, or None if the service is unavailable.

    Never fatal: without embeddings concepts still deduplicate on slug, which
    catches most of the duplicates anyway. Losing the fuzzy match is much
    better than losing the whole lesson's concepts.
    """
    try:
        from services.embedding_service import get_embedding_service
        service = get_embedding_service()
        return service.embed_text(text) if service else None
    except Exception as exc:
        logger.warning(f"Concept embedding unavailable: {exc}")
        return None


def _find_or_create_concept(db, user_id: int, spec: Dict) -> Concept:
    """One row per idea, however the model chose to phrase it this time.

    Two passes: exact slug, then nearest neighbour by embedding. The slug
    catches casing and articles for free; the embedding catches "light
    reactions" against "light-dependent reactions", which slugging never
    would. Without both, the concept table fills with near-duplicates and
    mastery is split across them - the student looks like they know three
    things slightly rather than one thing well.
    """
    existing = (
        db.query(Concept)
        .filter(Concept.user_id == user_id, Concept.slug == spec["slug"])
        .first()
    )
    if existing:
        return existing

    embedding = _embed(spec["name"])
    if embedding is not None:
        near = (
            db.query(Concept)
            .filter(Concept.user_id == user_id, Concept.embedding.isnot(None))
            .order_by(Concept.embedding.cosine_distance(embedding))
            .limit(1)
            .first()
        )
        if near is not None and near.embedding is not None:
            similarity = _cosine(embedding, list(near.embedding))
            if similarity >= CONCEPT_MERGE_THRESHOLD and _distinguishing_tokens(
                spec["name"], near.name
            ):
                logger.info(
                    f"Not merging {spec['name']!r} with {near.name!r} despite "
                    f"similarity {similarity:.3f} - they differ meaningfully"
                )
            elif similarity >= CONCEPT_MERGE_THRESHOLD:
                logger.info(
                    f"Merging concept {spec['name']!r} into existing "
                    f"{near.name!r} (similarity {similarity:.3f})"
                )
                return near

    concept = Concept(
        user_id=user_id,
        name=spec["name"],
        slug=spec["slug"],
        description=spec.get("description"),
        embedding=embedding,
    )
    db.add(concept)
    db.flush()
    return concept


# Tokens that carry the whole distinction between two otherwise identical
# concept names. Embeddings put "Newton's First Law" and "Newton's Second
# Law" at 0.90 similarity - close enough to merge under any threshold loose
# enough to also merge "binary search process" with "binary search
# algorithm", which is a merge worth having.
_ORDINALS = {
    "first", "second", "third", "fourth", "fifth", "sixth", "seventh",
    "eighth", "ninth", "tenth", "1st", "2nd", "3rd", "4th", "5th",
    "i", "ii", "iii", "iv", "v",
}
_NEGATIONS = ("in", "un", "non", "anti", "de", "a")


def _distinguishing_tokens(a: str, b: str) -> bool:
    """True when two names differ in a way that must not be merged.

    Two failure modes, both of which would silently credit mastery of one
    idea to another the student has never studied:

      ordinals   Newton's First Law  vs  Newton's Second Law
      negation   light-dependent     vs  light-independent

    Anything else close enough to pass the similarity threshold is a
    genuine restatement and should merge.
    """
    ta = {t for t in re.split(r"[^a-z0-9]+", a.lower()) if t}
    tb = {t for t in re.split(r"[^a-z0-9]+", b.lower()) if t}
    only_a, only_b = ta - tb, tb - ta

    # An ordinal or digit present on one side and not the other.
    for side in (only_a, only_b):
        if side & _ORDINALS or any(t.isdigit() for t in side):
            return True

    # A negated form of a word the other side has plainly.
    for x in only_a:
        for y in only_b:
            for prefix in _NEGATIONS:
                if x == prefix + y or y == prefix + x:
                    return True
    return False


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def _ensure_mastery(db, user_id: int, concept_id: int) -> None:
    """A concept the student has been taught but never reviewed is at zero,
    not absent - the difference matters when deciding what to teach next."""
    row = (
        db.query(ConceptMastery)
        .filter(ConceptMastery.user_id == user_id, ConceptMastery.concept_id == concept_id)
        .first()
    )
    if row is None:
        db.add(ConceptMastery(
            user_id=user_id,
            concept_id=concept_id,
            strength=0.0,
            first_seen_at=datetime.now(timezone.utc),
        ))
        # Flush immediately. This session is autoflush=False, and a concept
        # taught in several scenes reaches here once per scene - without the
        # flush the second call cannot see the first call's pending row,
        # inserts a duplicate, and the unique constraint takes the whole
        # lesson's processing down at commit.
        db.flush()


@celery_app.task(bind=True, max_retries=1, default_retry_delay=60)
def process_lesson_review_task(self, lesson_id: int) -> dict:
    """Tag a finished lesson with concepts and generate its review items."""
    logger.info(f"Post-processing lesson {lesson_id} for concepts and review items")
    db = SessionLocal()
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            return {"status": "error", "message": f"lesson {lesson_id} not found"}
        if lesson.status != LessonStatus.COMPLETED:
            return {"status": "skipped", "message": "lesson is not completed"}
        if db.query(ReviewItem).filter(ReviewItem.lesson_id == lesson_id).first():
            return {"status": "skipped", "message": "already processed"}

        scenes = lesson.scenes or []
        if not scenes:
            return {"status": "skipped", "message": "lesson has no scenes"}

        llm = _make_llm_callable(lesson.user_id)

        # ---- concepts
        # Non-fatal. Questions are the part the student actually uses; losing
        # the concept tags costs adaptivity later, but losing the questions
        # because a tagging response came back malformed would be a much
        # worse trade.
        try:
            by_scene, edges = asyncio.run(
                extract_concepts(llm, lesson.title or lesson.requirement, scenes)
            )
        except Exception as exc:
            logger.warning(
                f"Concept extraction failed for lesson {lesson_id}, "
                f"generating review items without concept tags: {exc}"
            )
            by_scene, edges = {}, []

        concepts_by_slug: Dict[str, Concept] = {}
        for scene_id, specs in by_scene.items():
            for spec in specs:
                concept = _find_or_create_concept(db, lesson.user_id, spec)
                concepts_by_slug[spec["slug"]] = concept
                _ensure_mastery(db, lesson.user_id, concept.id)
                exists = (
                    db.query(SceneConcept)
                    .filter(
                        SceneConcept.lesson_id == lesson_id,
                        SceneConcept.scene_id == scene_id,
                        SceneConcept.concept_id == concept.id,
                    )
                    .first()
                )
                if not exists:
                    db.add(SceneConcept(
                        lesson_id=lesson_id,
                        scene_id=scene_id,
                        concept_id=concept.id,
                        is_primary=spec.get("primary", True),
                    ))
        db.commit()

        # ---- prerequisite edges, skipping anything that would form a cycle
        for before_slug, after_slug in edges:
            before = concepts_by_slug.get(before_slug)
            after = concepts_by_slug.get(after_slug)
            if not before or not after or before.id == after.id:
                continue
            if _would_cycle(db, lesson.user_id, before.id, after.id):
                logger.info(
                    f"Skipping prerequisite {before.name!r} -> {after.name!r}: "
                    "it would create a cycle"
                )
                continue
            exists = (
                db.query(ConceptEdge)
                .filter(
                    ConceptEdge.prerequisite_id == before.id,
                    ConceptEdge.dependent_id == after.id,
                )
                .first()
            )
            if not exists:
                db.add(ConceptEdge(
                    user_id=lesson.user_id,
                    prerequisite_id=before.id,
                    dependent_id=after.id,
                ))
        db.commit()

        # ---- review items
        created = 0
        for scene in scenes:
            if created >= MAX_ITEMS_PER_LESSON:
                break
            if not scene_is_substantive(scene):
                continue
            scene_id = scene.get("id")
            specs = by_scene.get(scene_id, [])
            names = [s["name"] for s in specs if s.get("primary", True)]
            concept_id = None
            if specs:
                primary = next((s for s in specs if s.get("primary", True)), specs[0])
                found = concepts_by_slug.get(primary["slug"])
                concept_id = found.id if found else None

            try:
                items = asyncio.run(generate_items(
                    llm, lesson.title or lesson.requirement, scene, names,
                    count=ITEMS_PER_SCENE,
                ))
            except Exception as exc:
                # One bad scene must not cost the whole lesson its review
                # queue - the same reasoning as skipping a failed Manim scene.
                logger.warning(f"Item generation failed for scene {scene_id}: {exc}")
                continue

            for item in items:
                if created >= MAX_ITEMS_PER_LESSON:
                    break
                db.add(ReviewItem(
                    user_id=lesson.user_id,
                    lesson_id=lesson_id,
                    scene_id=scene_id,
                    concept_id=concept_id,
                    notebook_id=lesson.notebook_id,
                    kind=ReviewKind(item["kind"]),
                    prompt=item["prompt"],
                    answer=item["answer"],
                    rubric=item["rubric"],
                ))
                created += 1
        db.commit()

        logger.info(
            f"Lesson {lesson_id}: {len(concepts_by_slug)} concepts, {created} review items"
        )
        return {
            "status": "success",
            "concepts": len(concepts_by_slug),
            "items": created,
        }

    except Exception as exc:
        logger.error(f"Review post-processing failed for lesson {lesson_id}: {exc}")
        db.rollback()
        # Retry once; a lesson without review items is degraded, not broken,
        # so this never marks the lesson itself as failed.
        try:
            self.retry(exc=exc)
        except Exception:
            pass
        return {"status": "error", "message": str(exc)}
    finally:
        db.close()


def _would_cycle(db, user_id: int, before_id: int, after_id: int) -> bool:
    """True if before -> after would make the prerequisite graph cyclic.

    Walks forward from `after`: if `before` is reachable, adding this edge
    closes a loop, and a cyclic prerequisite graph means no valid teaching
    order exists at all.
    """
    seen = {after_id}
    frontier = [after_id]
    while frontier:
        rows = (
            db.query(ConceptEdge.dependent_id)
            .filter(
                ConceptEdge.user_id == user_id,
                ConceptEdge.prerequisite_id.in_(frontier),
            )
            .all()
        )
        nxt = [r[0] for r in rows if r[0] not in seen]
        if before_id in nxt:
            return True
        seen.update(nxt)
        frontier = nxt
    return False
