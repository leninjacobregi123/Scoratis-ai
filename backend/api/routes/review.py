"""
Review routes: what is due, answering it, and what that does to the schedule.

The whole point of spaced repetition is that the queue decides what to show,
not the student - so there is no "browse all questions" endpoint here. You
ask what is due, you answer it, and the scheduler decides when it comes back.

Grading is split by kind: multiple choice is compared exactly, with no model
call and no latency, while free recall goes to the model against the rubric
stored with the item. A student should never wait on an LLM to be told they
picked option B correctly.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_

from core.auth import get_current_user
from database import get_database
from models import (
    ReviewItem, ReviewSchedule, ReviewLog, ReviewKind,
    ConceptMastery, Concept, User,
)
from services.review.scheduler import (
    new_state, review as apply_review, mastery_strength,
)
from services.review.extractor import grade_response, grade_mcq

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/review", tags=["review"])

# How many items one sitting offers. Long enough to be worth starting,
# short enough to finish - an unbounded queue is how review backlogs become
# something people avoid opening.
SESSION_LIMIT = 20


async def _owned_item(session, item_id: int, user: User) -> ReviewItem:
    """404 for both missing and other users' items - a different status
    would leak which item ids exist."""
    item = await session.get(ReviewItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Review item not found")
    return item


async def _make_llm_callable(session, user_id: int):
    """Async (system, user, max_tokens) -> str bound to this user's provider.

    Same resolution rule as tasks/lesson_tasks._make_llm_callable - the
    user's default or most recent active provider - but read through the
    request's async session rather than a worker's sync one. There is no
    app-wide fallback provider by design.
    """
    from models import LLMProviderConfig, ProviderType, PROVIDER_INFO
    from services.litellm_service import get_litellm_service

    cfg = (await session.execute(
        select(LLMProviderConfig)
        .where(
            LLMProviderConfig.user_id == user_id,
            LLMProviderConfig.is_active == True,  # noqa: E712
        )
        .order_by(
            LLMProviderConfig.is_default.desc(),
            LLMProviderConfig.updated_at.desc(),
        )
        .limit(1)
    )).scalar_one_or_none()

    if not cfg:
        raise HTTPException(
            status_code=400,
            detail="No AI provider configured - add one in AI Settings to have "
                   "written answers marked.",
        )

    provider = (
        cfg.provider if isinstance(cfg.provider, ProviderType)
        else ProviderType(cfg.provider)
    )
    model = (cfg.extra_settings or {}).get("default_model") or next(
        iter(PROVIDER_INFO.get(provider, {}).get("models", [])), None
    )
    if not model:
        raise HTTPException(
            status_code=400,
            detail=f"No model configured for the {provider.value} provider.",
        )

    svc = get_litellm_service()
    key, base_url = cfg.api_key_encrypted, cfg.base_url

    async def call(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        return await svc.generate(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            provider=provider,
            model=model,
            api_key_encrypted=key,
            base_url=base_url,
            max_tokens=max_tokens,
            temperature=0.2,
            timeout=60,
        )

    return call


@router.get("/due")
async def due_items(
    notebook_id: Optional[int] = None,
    limit: int = Query(SESSION_LIMIT, le=50),
    current_user: User = Depends(get_current_user),
):
    """The next items to answer, soonest-overdue first.

    Items that have never been scheduled are due immediately - a question
    generated an hour ago should appear in the next session, not wait for a
    schedule row that only exists once it has been answered.
    """
    db = get_database()
    now = datetime.now(timezone.utc)
    async with db.get_session() as session:
        query = (
            select(ReviewItem, ReviewSchedule)
            .outerjoin(ReviewSchedule, ReviewSchedule.item_id == ReviewItem.id)
            .where(
                ReviewItem.user_id == current_user.id,
                ReviewItem.retired_at.is_(None),
                or_(ReviewSchedule.id.is_(None), ReviewSchedule.due_at <= now),
            )
        )
        if notebook_id is not None:
            query = query.where(ReviewItem.notebook_id == notebook_id)

        rows = (await session.execute(
            query.order_by(ReviewSchedule.due_at.asc().nullsfirst(), ReviewItem.id)
                 .limit(limit)
        )).all()

        return {
            "items": [item.to_dict() for item, _ in rows],
            "count": len(rows),
        }


@router.get("/stats")
async def review_stats(
    notebook_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
):
    """Due count and mastery summary - drives the badge and the dashboard."""
    db = get_database()
    now = datetime.now(timezone.utc)
    async with db.get_session() as session:
        base = select(func.count()).select_from(ReviewItem).outerjoin(
            ReviewSchedule, ReviewSchedule.item_id == ReviewItem.id
        ).where(
            ReviewItem.user_id == current_user.id,
            ReviewItem.retired_at.is_(None),
        )
        if notebook_id is not None:
            base = base.where(ReviewItem.notebook_id == notebook_id)

        total = await session.scalar(base)
        due = await session.scalar(
            base.where(or_(ReviewSchedule.id.is_(None), ReviewSchedule.due_at <= now))
        )

        mastery_rows = (await session.execute(
            select(ConceptMastery, Concept)
            .join(Concept, Concept.id == ConceptMastery.concept_id)
            .where(ConceptMastery.user_id == current_user.id)
            .order_by(ConceptMastery.strength.desc())
        )).all()

        concepts = [
            {**m.to_dict(), "name": c.name} for m, c in mastery_rows
        ]
        known = sum(1 for c in concepts if c["strength"] >= 0.6)

        return {
            "due": due or 0,
            "total": total or 0,
            "concepts_tracked": len(concepts),
            "concepts_known": known,
            "concepts": concepts[:50],
        }


@router.post("/{item_id}/answer")
async def answer_item(
    item_id: int, payload: dict, current_user: User = Depends(get_current_user)
):
    """Grade an answer, advance the schedule, update concept mastery.

    The client may pass an explicit `grade` for self-assessment (the classic
    flashcard "I knew that / I didn't"), otherwise the response is marked -
    exactly for multiple choice, by the model for free recall.
    """
    response_text = str(payload.get("response") or "").strip()
    explicit_grade = payload.get("grade")

    db = get_database()
    now = datetime.now(timezone.utc)
    async with db.get_session() as session:
        item = await _owned_item(session, item_id, current_user)

        # ---- grade
        feedback = ""
        if explicit_grade is not None:
            try:
                grade = int(explicit_grade)
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail="grade must be 1-4")
            if grade not in (1, 2, 3, 4):
                raise HTTPException(status_code=400, detail="grade must be 1-4")
        elif not response_text:
            raise HTTPException(status_code=400, detail="response or grade is required")
        elif item.kind == ReviewKind.MCQ:
            grade, feedback = grade_mcq(response_text, item.answer)
        else:
            must = (item.rubric or {}).get("must_include", [])
            try:
                llm = await _make_llm_callable(session, current_user.id)
                grade, feedback = await grade_response(
                    llm, item.prompt, item.answer, must, response_text,
                )
            except HTTPException:
                raise
            except Exception as exc:
                # Never strand the student mid-session on a grading failure.
                # Self-assessment is a worse signal than a marked one, but it
                # is a far better outcome than an unanswerable question.
                logger.warning(f"Grading failed for item {item_id}: {exc}")
                raise HTTPException(
                    status_code=503,
                    detail="Could not mark that answer just now - try again, "
                           "or grade yourself to keep going.",
                )

        # ---- advance the schedule
        schedule = (await session.execute(
            select(ReviewSchedule).where(ReviewSchedule.item_id == item_id)
        )).scalar_one_or_none()

        state = new_state() if schedule is None else {
            "stability": schedule.stability,
            "difficulty": schedule.difficulty,
            "reps": schedule.reps,
            "lapses": schedule.lapses,
            "last_grade": schedule.last_grade,
        }
        last_reviewed = schedule.last_reviewed_at if schedule else None
        result = apply_review(state, grade, now=now, last_reviewed_at=last_reviewed)

        if schedule is None:
            schedule = ReviewSchedule(item_id=item_id, user_id=current_user.id)
            session.add(schedule)
        schedule.due_at = result["due_at"]
        schedule.stability = result["stability"]
        schedule.difficulty = result["difficulty"]
        schedule.reps = result["reps"]
        schedule.lapses = result["lapses"]
        schedule.last_grade = grade
        schedule.last_reviewed_at = now

        session.add(ReviewLog(
            item_id=item_id,
            user_id=current_user.id,
            grade=grade,
            response_text=response_text or None,
            feedback=feedback or None,
            scheduled_days=result["interval_days"],
            elapsed_days=result["elapsed_days"],
        ))

        # ---- roll up into concept mastery
        if item.concept_id:
            mastery = (await session.execute(
                select(ConceptMastery).where(
                    ConceptMastery.user_id == current_user.id,
                    ConceptMastery.concept_id == item.concept_id,
                )
            )).scalar_one_or_none()
            if mastery is None:
                mastery = ConceptMastery(
                    user_id=current_user.id,
                    concept_id=item.concept_id,
                    first_seen_at=now,
                )
                session.add(mastery)
            mastery.strength = mastery_strength(
                result["stability"], result["lapses"], result["reps"]
            )
            mastery.review_count = (mastery.review_count or 0) + 1
            if grade == 1:
                mastery.lapse_count = (mastery.lapse_count or 0) + 1
            mastery.last_reviewed_at = now

        await session.flush()

        return {
            "grade": grade,
            "feedback": feedback,
            "correct_answer": item.answer,
            "next_due": result["due_at"].isoformat(),
            "interval_days": round(result["interval_days"], 3),
        }


@router.post("/{item_id}/retire")
async def retire_item(item_id: int, current_user: User = Depends(get_current_user)):
    """Drop an item from the rotation without losing its history.

    Generated questions are occasionally wrong or ambiguous, and a student
    who cannot remove one is stuck being asked it forever. Retiring rather
    than deleting keeps its review_log entries interpretable.
    """
    db = get_database()
    async with db.get_session() as session:
        item = await _owned_item(session, item_id, current_user)
        item.retired_at = datetime.now(timezone.utc)
        await session.flush()
        return {"id": item_id, "retired": True}
