"""
Shared helper for starting a Celery-backed video generation job.

Every endpoint that used to call video_service.start_generation() (the old
in-memory-tracked, maestro-studio-dependent pipeline) now goes through this
instead. See backend/tasks_pkg/video_tasks.py for the actual rendering.
"""
import logging
from typing import Any, Dict, Optional

from database import get_database
from models import VideoJob

logger = logging.getLogger(__name__)


async def start_video_job(
    user_id: int,
    topic: str,
    quality: str = "high",
    duration: int = 20,
    context: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    auto_generated: bool = False,
) -> int:
    """
    Create a VideoJob row and enqueue the Celery render task.

    Runs in its own short transaction rather than reusing a caller-supplied
    session, so the row is guaranteed committed before the task is enqueued -
    enqueueing from inside a still-open transaction risks the worker querying
    for a row that isn't visible to other connections yet.

    Returns the job id (used as the polling identifier, same role the old
    system's task_id string played).
    """
    from tasks_pkg.video_tasks import render_video_task

    db = get_database()
    async with db.get_session() as session:
        job = VideoJob(
            user_id=user_id,
            topic=topic.strip(),
            session_id=session_id,
            quality=quality,
            duration_seconds=duration,
            auto_generated=auto_generated,
            context=context,
        )
        session.add(job)
        await session.flush()
        job_id = job.id

    render_video_task.delay(job_id)
    logger.info(f"Queued video job {job_id} for user {user_id}: '{topic}'")
    return job_id
