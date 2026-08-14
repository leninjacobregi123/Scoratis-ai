"""
Lesson routes: create, poll, fetch, list, delete.

Generation is a multi-minute Celery job, so create returns immediately with an
id and the client polls GET /lessons/{id} - same contract the video UI already
uses, so the frontend polling code is familiar.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from core.auth import get_current_user
from database import get_database
from models import Lesson, LessonStatus, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lessons", tags=["lessons"])


async def _owned_lesson(session, lesson_id: int, user: User) -> Lesson:
    """Fetch a lesson, 404ing for both missing AND other users' rows.

    Deliberately does not distinguish the two: a different status code would
    leak which lesson ids exist.
    """
    lesson = await session.get(Lesson, lesson_id)
    if not lesson or lesson.user_id != user.id:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@router.post("", status_code=202)
async def create_lesson(payload: dict, current_user: User = Depends(get_current_user)):
    """Queue a lesson. 202 because the work has been accepted, not finished."""
    requirement = (payload.get("requirement") or "").strip()
    if not requirement:
        raise HTTPException(status_code=400, detail="requirement is required")
    if len(requirement) > 2000:
        raise HTTPException(status_code=400, detail="requirement is too long (max 2000 chars)")

    db = get_database()
    async with db.get_session() as session:
        lesson = Lesson(
            user_id=current_user.id,
            requirement=requirement,
            session_id=payload.get("session_id"),
            status=LessonStatus.PENDING,
            message="Queued",
        )
        session.add(lesson)
        await session.flush()
        lesson_id = lesson.id

    # Enqueued only after the row is committed - a worker picking this up
    # before the INSERT is visible would 404 on its own lesson.
    from tasks.lesson_tasks import generate_lesson_task
    generate_lesson_task.delay(lesson_id)
    logger.info(f"Queued lesson {lesson_id} for user {current_user.id}: '{requirement[:60]}'")

    return {"id": lesson_id, "status": "pending", "message": "Lesson generation started"}


@router.get("")
async def list_lessons(
    session_id: str | None = None,
    current_user: User = Depends(get_current_user),
):
    """Recent lessons. Scenes omitted - a full lesson's slide JSON is large
    enough that returning it per row would dominate the response.

    `session_id` narrows this to the lessons the agent built inside one chat
    thread. The chat holds the lesson->message link only in memory, so
    reopening a conversation has to rebuild it from here or the lesson cards
    disappear from a thread that plainly produced them.
    """
    db = get_database()
    async with db.get_session() as session:
        query = select(Lesson).where(Lesson.user_id == current_user.id)
        if session_id:
            query = query.where(Lesson.session_id == session_id)
        rows = (await session.execute(
            query.order_by(Lesson.created_at.desc()).limit(50)
        )).scalars().all()
        return {"lessons": [l.to_dict(include_scenes=False) for l in rows]}


@router.get("/{lesson_id}")
async def get_lesson(lesson_id: int, current_user: User = Depends(get_current_user)):
    """Full lesson including scenes. Doubles as the progress-poll endpoint."""
    db = get_database()
    async with db.get_session() as session:
        lesson = await _owned_lesson(session, lesson_id, current_user)
        return lesson.to_dict(include_scenes=True)


@router.post("/{lesson_id}/progress")
async def update_progress(
    lesson_id: int, payload: dict, current_user: User = Depends(get_current_user)
):
    """Record that the learner finished a scene, and/or where they are now.

    `completed_scene_id` is unioned into the existing set rather than
    replacing it, so replaying a scene can never *un*-complete others and two
    tabs can't clobber each other's progress.
    """
    db = get_database()
    async with db.get_session() as session:
        lesson = await _owned_lesson(session, lesson_id, current_user)

        scene_id = payload.get("completed_scene_id")
        if scene_id:
            valid_ids = {s.get("id") for s in (lesson.scenes or [])}
            if scene_id not in valid_ids:
                raise HTTPException(status_code=400, detail="Unknown scene id")
            done = list(lesson.completed_scene_ids or [])
            if scene_id not in done:
                done.append(scene_id)
                # Reassigning (not mutating) so SQLAlchemy flags the JSONB
                # column dirty - an in-place append would not be persisted.
                lesson.completed_scene_ids = done

        idx = payload.get("last_scene_index")
        if isinstance(idx, int) and 0 <= idx < len(lesson.scenes or []):
            lesson.last_scene_index = idx

        return {
            "completed_scene_ids": lesson.completed_scene_ids or [],
            "completed_count": len(lesson.completed_scene_ids or []),
            "scene_count": len(lesson.scenes or []),
            "last_scene_index": lesson.last_scene_index or 0,
        }


@router.delete("/{lesson_id}")
async def delete_lesson(lesson_id: int, current_user: User = Depends(get_current_user)):
    db = get_database()
    async with db.get_session() as session:
        lesson = await _owned_lesson(session, lesson_id, current_user)
        await session.delete(lesson)
    return {"message": "Lesson deleted"}
