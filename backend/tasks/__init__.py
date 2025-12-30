"""
Celery Tasks for Scoratis
"""

from .ingestion_tasks import (
    process_document_task,
    generate_embeddings_task,
    process_batch_documents_task,
)

__all__ = [
    "process_document_task",
    "generate_embeddings_task",
    "process_batch_documents_task",
]
