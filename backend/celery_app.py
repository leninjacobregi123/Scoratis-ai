"""
Celery Configuration for Scoratis
Background task processing for document ingestion and embedding generation
"""

from celery import Celery
from config import settings

# Create Celery app
celery_app = Celery(
    "scoratis",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["tasks.ingestion_tasks"],
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
}


if __name__ == "__main__":
    celery_app.start()
