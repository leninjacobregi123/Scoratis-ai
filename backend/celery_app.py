"""
Celery Configuration for Scoratis
Background task processing for document ingestion and embedding generation
"""

import os
import sys

# The `celery` console script's sys.path[0] is its own directory
# (.venv/bin/), not backend/ - Celery's CLI fixes this up for its own
# app-loading, but forked prefork worker processes don't reliably inherit
# that fixup, which breaks lazy `from llm_service import llm_service`-style
# imports elsewhere (e.g. video_service.py) at task-execution time even
# though this module and its own `include=[...]` targets import fine at
# worker startup. Make it unconditional here instead of chasing pool
# implementation details.
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from celery import Celery
from celery.signals import worker_process_init
from config import settings


@worker_process_init.connect
def _fixup_worker_sys_path(**kwargs):
    """
    Re-apply the backend/ sys.path fixup inside each forked/spawned worker
    process. billiard's prefork pool does not reliably inherit sys.path
    mutations made in the parent before forking (observed directly: a
    plain `sys.path.insert()` above this line, which the parent process
    picks up fine, is simply absent from the child's sys.path at task
    execution time) - this signal is the supported per-child-process hook.
    """
    if _BACKEND_DIR not in sys.path:
        sys.path.insert(0, _BACKEND_DIR)

# Create Celery app
celery_app = Celery(
    "scoratis",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["tasks.ingestion_tasks", "tasks.video_tasks", "tasks.lesson_tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task routing
    task_routes={
        "tasks.ingestion_tasks.*": {"queue": "ingestion"},
        "tasks.video_tasks.*": {"queue": "video"},
        # Lessons render videos inline, so they share the video queue's
        # concurrency budget rather than competing with it on another.
        "tasks.lesson_tasks.*": {"queue": "video"},
    },

    # Task defaults
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",

    # Retry policy
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Rate limiting and concurrency
    worker_prefetch_multiplier=1,
    worker_concurrency=2,

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour

    # Task time limits
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,  # 10 minutes hard limit

    # Beat scheduler (for periodic tasks if needed)
    beat_schedule={},
)

# Task retry settings
celery_app.conf.task_annotations = {
    "tasks.ingestion_tasks.process_document_task": {
        "rate_limit": "10/m",
        "max_retries": 3,
        "default_retry_delay": 60,
    },
    "tasks.ingestion_tasks.generate_embeddings_task": {
        "rate_limit": "20/m",
        "max_retries": 3,
        "default_retry_delay": 30,
    },
    # Video rendering (script gen + Manim render + ffmpeg mux) runs minutes,
    # not seconds - the global 300s/600s limits above would kill it mid-render.
    "tasks.video_tasks.render_video_task": {
        "rate_limit": "5/m",
        "max_retries": 1,
        "default_retry_delay": 30,
        "soft_time_limit": 1800,
        "time_limit": 2100,
    },
    # A lesson is the sum of its parts: ~15 LLM calls plus up to two full
    # Manim renders, which it invokes IN-PROCESS (see lesson_tasks.
    # _render_video_scene - dispatching a sub-task would deadlock a
    # single-slot pool). So its budget has to cover every render it triggers,
    # not just its own orchestration. On the global 300s soft limit the
    # second animation was being killed mid-render and silently degraded to
    # a slide.
    "tasks.lesson_tasks.generate_lesson_task": {
        "max_retries": 0,
        "soft_time_limit": 3600,
        "time_limit": 3900,
    },
}


if __name__ == "__main__":
    celery_app.start()
