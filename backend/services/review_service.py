"""
Spaced-repetition review queue using the SM-2 algorithm (SuperMemo 2).

SM-2 reference: quality is graded 0-5. On quality >= 3 the item was
recalled - interval and ease factor grow. On quality < 3 it wasn't -
repetitions resets and the item comes back tomorrow.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import ReviewItem, ReviewSourceType

logger = logging.getLogger(__name__)

MIN_EASE_FACTOR = 1.3


async def seed_from_key_discoveries(
    db: AsyncSession,
    *,
    user_id: int,
    discoveries: List[str],
) -> int:
    """Create a due-now ReviewItem for each newly confirmed concept that
    doesn't already have one for this user. Returns count created."""
    if not discoveries:
        return 0

    existing = await db.execute(
        select(ReviewItem.concept).where(
            ReviewItem.user_id == user_id,
            ReviewItem.source_type == ReviewSourceType.KEY_DISCOVERY,
        )
    )
    existing_concepts = {row[0] for row in existing.all()}

    created = 0
    for concept in discoveries:
        concept = (concept or "").strip()
        if not concept or concept in existing_concepts:
            continue
        db.add(ReviewItem(
            user_id=user_id,
            concept=concept,
            source_type=ReviewSourceType.KEY_DISCOVERY,
        ))
        existing_concepts.add(concept)
        created += 1

    if created:
        await db.flush()
    return created


async def seed_from_missed_quiz_questions(
    db: AsyncSession,
    *,
    user_id: int,
    questions: list,
) -> int:
    """`questions` is a list of QuizQuestion objects the user answered wrong."""
    if not questions:
        return 0

    question_ids = [q.id for q in questions]
    existing = await db.execute(
        select(ReviewItem.source_id).where(
            ReviewItem.user_id == user_id,
            ReviewItem.source_type == ReviewSourceType.QUIZ_QUESTION,
            ReviewItem.source_id.in_(question_ids),
        )
    )
    existing_ids = {row[0] for row in existing.all()}

    created = 0
    for q in questions:
        if q.id in existing_ids:
            continue
        db.add(ReviewItem(
            user_id=user_id,
            concept=q.question_text,
            source_type=ReviewSourceType.QUIZ_QUESTION,
            source_id=q.id,
        ))
        created += 1

    if created:
        await db.flush()
    return created


def _apply_sm2(item: ReviewItem, quality: int) -> None:
    quality = max(0, min(5, quality))
    now = datetime.now(timezone.utc)

    if quality < 3:
        item.repetitions = 0
        item.interval_days = 1
    else:
        if item.repetitions == 0:
            item.interval_days = 1
        elif item.repetitions == 1:
            item.interval_days = 6
        else:
            item.interval_days = round(item.interval_days * item.ease_factor)
        item.repetitions += 1

    new_ease = item.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    item.ease_factor = max(MIN_EASE_FACTOR, new_ease)

    item.last_reviewed_at = now
    item.due_at = now + timedelta(days=item.interval_days)


async def grade_review_item(
    db: AsyncSession,
    *,
    item: ReviewItem,
    quality: int,
) -> ReviewItem:
    _apply_sm2(item, quality)
    await db.flush()
    return item


async def get_due_items(
    db: AsyncSession,
    *,
    user_id: int,
    limit: int = 50,
) -> List[ReviewItem]:
    stmt = select(ReviewItem).where(
        ReviewItem.user_id == user_id,
        ReviewItem.due_at <= datetime.now(timezone.utc),
    ).order_by(ReviewItem.due_at.asc()).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())
