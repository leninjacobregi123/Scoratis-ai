"""
Video generation routes - Celery-backed, replacing the old in-memory/
simulated pipeline in video_service.py (see services/video_job_service.py
and tasks_pkg/video_tasks.py for the real implementation).

Keeps the same URL shape and response fields the frontend already polls
(POST /videos/generate -> {task_id}, GET /videos/status/{task_id} ->
{status, stage, progress, video_path, ...}) so no frontend changes were
needed for the base generate/poll flow.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_pkg.auth import get_current_user, get_db
from models import User, VideoJob, VideoJobStatus
from services.video_job_service import start_video_job

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/videos", tags=["videos"])


class VideoGenerateRequest(BaseModel):
    topic: str
    quality: Optional[str] = "high"
    duration: Optional[int] = 90


def _job_status_dict(job: VideoJob) -> dict:
    # Frontend checks `status.status === 'error'` (matching the old
    # GenerationStage.ERROR string) - translate the DB enum's "failed"
    # rather than changing the frontend's already-working check.
    status_str = "error" if job.status == VideoJobStatus.FAILED else job.status.value
    return {
        "task_id": job.id,
        "topic": job.topic,
        "status": status_str,
        "stage": job.stage,
        "progress": job.progress_percent,
        "message": job.message,
        "video_path": job.video_path,
        "error": job.error_message,
        "log_entry": job.message,
    }


@router.post("/generate")
async def generate_video(request: VideoGenerateRequest, current_user: User = Depends(get_current_user)):
    """Start video generation task"""
    if not request.topic.strip():
        raise HTTPException(status_code=400, detail="Topic is required")

    job_id = await start_video_job(
        user_id=current_user.id,
        topic=request.topic.strip(),
        quality=request.quality or "high",
        duration=request.duration or 90,
    )

    return {
        "task_id": job_id,
        "message": "Video generation started",
        "topic": request.topic,
    }


@router.get("/status/{task_id}")
async def get_generation_status(
    task_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get status of a video generation task"""
    result = await session.execute(select(VideoJob).where(VideoJob.id == task_id))
    job = result.scalar_one_or_none()

    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")

    return _job_status_dict(job)


@router.get("/generated")
async def get_generated_videos(
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get list of completed videos for the current user"""
    result = await session.execute(
        select(VideoJob)
        .where(VideoJob.user_id == current_user.id, VideoJob.status == VideoJobStatus.COMPLETED)
        .order_by(VideoJob.created_at.desc())
        .limit(limit)
    )
    jobs = result.scalars().all()

    return {
        "videos": [
            {
                "id": job.id,
                "path": job.video_path,
                "topic": job.topic,
                "duration": job.duration_seconds,
                "created_at": job.created_at.isoformat() if job.created_at else None,
            }
            for job in jobs
        ]
    }
