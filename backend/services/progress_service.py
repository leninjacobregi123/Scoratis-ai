"""
Per-subject progress tracking.

Upserted incrementally as it happens (a chat turn completes, a quiz is
scored) rather than computed live from a group-by over conversations/
messages every time the dashboard loads - the same reasoning documented
on the SubjectProgress model.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import SubjectProgress

logger = logging.getLogger(__name__)


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _mastery_from_state(state: dict) -> float:
    """Cheap heuristic from ConversationAnalyzer's per-session counters:
    understanding signals and confirmed discoveries push mastery up,
    unresolved confusion pulls it down. Not a psychometric model - a
    reasonable proxy until a real assessment-based score (e.g. quiz
    performance) accumulates."""
    understanding = state.get("understanding_signals", 0)
    confusion = state.get("confusion_count", 0)
    discoveries = len(state.get("key_discoveries", []) or [])
    return _clamp(understanding * 15 + discoveries * 20 - confusion * 8)


async def record_turn(
    db: AsyncSession,
    *,
    user_id: int,
    subject: str,
    session_id: str,
    state: dict,
) -> None:
    """Call after an AI turn is persisted for a session. `state` is
    ConversationAnalyzer's per-session state dict (turn_count,
    confusion_count, understanding_signals, key_discoveries, ...)."""
    subject = subject or "general"

    result = await db.execute(
        select(SubjectProgress).where(
            SubjectProgress.user_id == user_id, SubjectProgress.subject == subject
        )
    )
    progress = result.scalar_one_or_none()

    turn_mastery = _mastery_from_state(state)

    if progress is None:
        progress = SubjectProgress(
            user_id=user_id,
            subject=subject,
            mastery_score=turn_mastery,
            total_turns=1,
            total_sessions=1,
        )
        db.add(progress)
    else:
        # Blend rather than overwrite so one confused turn doesn't erase a
        # session's worth of prior progress.
        progress.mastery_score = _clamp(progress.mastery_score * 0.7 + turn_mastery * 0.3)
        progress.total_turns += 1
        if state.get("turn_count") == 1:
            progress.total_sessions += 1
        progress.last_active_at = datetime.now(timezone.utc)

    await db.flush()


async def record_quiz_result(
    db: AsyncSession,
    *,
    user_id: int,
    subject: str,
    score: float,
) -> None:
    subject = subject or "general"

    result = await db.execute(
        select(SubjectProgress).where(
            SubjectProgress.user_id == user_id, SubjectProgress.subject == subject
        )
    )
    progress = result.scalar_one_or_none()

    if progress is None:
        progress = SubjectProgress(
            user_id=user_id,
            subject=subject,
            mastery_score=_clamp(score),
            quizzes_taken=1,
            quiz_average=score,
        )
        db.add(progress)
    else:
        total_quizzes = progress.quizzes_taken + 1
        progress.quiz_average = (progress.quiz_average * progress.quizzes_taken + score) / total_quizzes
        progress.quizzes_taken = total_quizzes
        # Quiz performance is a stronger mastery signal than a single chat turn.
        progress.mastery_score = _clamp(progress.mastery_score * 0.5 + score * 0.5)
        progress.last_active_at = datetime.now(timezone.utc)

    await db.flush()
