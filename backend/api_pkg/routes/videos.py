"""
Video generation routes - Celery-backed, replacing the old in-memory/
simulated pipeline in video_service.py (see services/video_job_service.py
and tasks/video_tasks.py for the real implementation).

Keeps the same URL shape and response fields the frontend already polls
(POST /videos/generate -> {task_id}, GET /videos/status/{task_id} ->
{status, stage, progress, video_path, ...}) so no frontend changes were
needed for the base generate/poll flow.
"""
import logging
import os
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_pkg.auth import get_current_user, get_db
from models import User, VideoJob, VideoJobStatus
from services.video_job_service import start_video_job
from video_service import video_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/videos", tags=["videos"])

# Lazy-loaded YouTube API client, self-contained singleton (mirrors the
# get_database()/get_rag_service() etc. pattern elsewhere in api_pkg/routes/)
_youtube_client = None


def get_youtube_client():
    """Lazy load YouTube API client"""
    global _youtube_client
    if _youtube_client is None:
        try:
            from googleapiclient.discovery import build
            api_key = os.getenv("YOUTUBE_API_KEY")
            if api_key:
                _youtube_client = build('youtube', 'v3', developerKey=api_key)
        except ImportError:
            pass
    return _youtube_client


def parse_youtube_duration(duration: str) -> str:
    """Parse YouTube duration format"""
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return "0:00"
    hours, minutes, seconds = match.groups()
    hours = int(hours) if hours else 0
    minutes = int(minutes) if minutes else 0
    seconds = int(seconds) if seconds else 0
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def format_view_count(count: int) -> str:
    """Format view count"""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


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


def _sample_video_search_result(q: str) -> dict:
    return {
        "videos": [
            {
                "video_id": "dQw4w9WgXcQ",
                "title": f"Educational Content: {q}",
                "channel": "Educational Channel",
                "thumbnail": "https://via.placeholder.com/320x180/8A2BE2/FFFFFF?text=Video",
                "description": f"Learn about {q}",
                "duration": "10:30",
                "view_count": "1.2M"
            }
        ],
        "source": "sample"
    }


@router.get("/search")
async def search_videos(
    q: str = Query(..., min_length=1),
    max_results: int = Query(12, le=25)
):
    """Search for videos"""
    youtube = get_youtube_client()

    if not youtube:
        return _sample_video_search_result(q)

    try:
        search_response = youtube.search().list(
            q=q,
            part='snippet',
            type='video',
            maxResults=max_results,
            order='relevance',
            safeSearch='moderate',
            videoEmbeddable='true'
        ).execute()

        video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]

        if not video_ids:
            return {"videos": [], "message": "No videos found"}

        videos_response = youtube.videos().list(
            part='statistics,contentDetails',
            id=','.join(video_ids)
        ).execute()

        video_details = {item['id']: item for item in videos_response.get('items', [])}

        formatted_videos = []
        for item in search_response.get('items', []):
            video_id = item['id']['videoId']
            snippet = item['snippet']
            details = video_details.get(video_id, {})

            duration = details.get('contentDetails', {}).get('duration', 'PT0S')
            view_count = int(details.get('statistics', {}).get('viewCount', '0'))

            formatted_videos.append({
                "video_id": video_id,
                "title": snippet['title'],
                "channel": snippet['channelTitle'],
                "thumbnail": snippet['thumbnails'].get('medium', {}).get('url', ''),
                "description": snippet.get('description', '')[:200],
                "duration": parse_youtube_duration(duration),
                "view_count": format_view_count(view_count)
            })

        return {"videos": formatted_videos, "source": "youtube"}

    except Exception as e:
        # A misconfigured/expired/quota-exceeded key must never surface as a
        # 500 to the user - degrade to the same sample fallback used when no
        # client is configured at all.
        logger.warning(f"YouTube search failed, falling back to sample results: {e}")
        return _sample_video_search_result(q)


@router.get("/detect-visuals")
async def detect_visuals(topic: str = Query(..., min_length=1)):
    """Detect what visual elements will be used for a topic"""
    visuals = video_service.detect_visuals(topic)
    return {"visuals": visuals, "topic": topic}
