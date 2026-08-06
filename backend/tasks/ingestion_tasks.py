"""
Celery Tasks for Document Ingestion
Background processing of documents for the RAG system
"""

import logging
from typing import List, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from celery_app import celery_app
from config import settings
from models import Document, Chunk, DocumentStatus
from services.ingestion_service import get_ingestion_service

logger = logging.getLogger(__name__)

# Create sync database session for Celery workers
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_recycle=1800)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document_task(self, document_id: int) -> dict:
    """
    Process a document: parse, generate summary, chunk, and create embeddings.

    Args:
        document_id: ID of the document to process

    Returns:
        Dictionary with processing results
    """
    logger.info(f"Starting document processing: document_id={document_id}")

    db = SessionLocal()
    try:
        # Fetch document
        document = db.query(Document).filter(Document.id == document_id).first()

        if not document:
            logger.error(f"Document not found: {document_id}")
            return {"status": "error", "message": "Document not found"}

        if document.status == DocumentStatus.COMPLETED:
            logger.info(f"Document already processed: {document_id}")
            return {"status": "skipped", "message": "Already processed"}

        # Update status to processing
        document.status = DocumentStatus.PROCESSING
        db.commit()

        ingestion_service = get_ingestion_service()

        # Step 1: Parse file if it's an upload
        if document.file_path and document.file_type:
            logger.info(f"Parsing file: {document.file_path}")
            try:
                parsed = ingestion_service.parse_file(
                    document.file_path,
                    document.file_type
                )
                document.content = parsed.content
                document.document_metadata = {
                    **(document.document_metadata or {}),
                    **parsed.metadata,
                    "page_count": parsed.page_count,
                    "word_count": parsed.word_count,
                }
                db.commit()
            except Exception as e:
                logger.error(f"Error parsing file: {e}")
                document.status = DocumentStatus.FAILED
                document.error_message = f"File parsing failed: {str(e)}"
                db.commit()
                raise self.retry(exc=e)

        # Step 2: Generate summary
        logger.info("Generating summary...")
        summary = ingestion_service.generate_summary(document.content)
        document.summary = summary

        # Step 3: Generate summary embedding
        logger.info("Generating summary embedding...")
        summary_embedding = ingestion_service.embedding_service.embed_text(summary)
        if summary_embedding:
            document.embedding = summary_embedding

        db.commit()

        # Step 4: Chunk the document
        logger.info("Chunking document...")
        chunks = ingestion_service.chunk_document(
            document.content,
            document.document_metadata
        )

        # Step 5: Generate chunk embeddings and save
        logger.info(f"Processing {len(chunks)} chunks...")
        chunk_texts = [chunk.content for chunk in chunks]
        chunk_embeddings = ingestion_service.batch_embed(chunk_texts)

        # Create chunk records
        for chunk_data, embedding in zip(chunks, chunk_embeddings):
            chunk = Chunk(
                document_id=document.id,
                chunk_index=chunk_data.chunk_index,
                content=chunk_data.content,
                chunk_metadata=chunk_data.metadata,
                embedding=embedding,
            )
            db.add(chunk)

        # Update document status
        document.status = DocumentStatus.COMPLETED
        document.error_message = None
        db.commit()

        logger.info(f"Document processed successfully: {document_id}, {len(chunks)} chunks created")

        return {
            "status": "success",
            "document_id": document_id,
            "chunks_created": len(chunks),
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing document {document_id}: {e}")

        # Update document status to failed
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = DocumentStatus.FAILED
                document.error_message = str(e)
                db.commit()
        except:
            pass

        raise self.retry(exc=e)

    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def generate_embeddings_task(self, document_id: int) -> dict:
    """
    Generate or regenerate embeddings for a document's chunks.

    Args:
        document_id: ID of the document

    Returns:
        Dictionary with results
    """
    logger.info(f"Generating embeddings for document: {document_id}")

    db = SessionLocal()
    try:
        # Fetch document and chunks
        document = db.query(Document).filter(Document.id == document_id).first()

        if not document:
            return {"status": "error", "message": "Document not found"}

        chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()

        if not chunks:
            return {"status": "error", "message": "No chunks found"}

        ingestion_service = get_ingestion_service()

        # Generate embeddings
        chunk_texts = [chunk.content for chunk in chunks]
        embeddings = ingestion_service.batch_embed(chunk_texts)

        # Update chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding

        # Also regenerate summary embedding
        if document.summary:
            summary_embedding = ingestion_service.embedding_service.embed_text(document.summary)
            if summary_embedding:
                document.embedding = summary_embedding

        db.commit()

        logger.info(f"Embeddings generated for document {document_id}: {len(chunks)} chunks")

        return {
            "status": "success",
            "document_id": document_id,
            "chunks_updated": len(chunks),
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error generating embeddings for document {document_id}: {e}")
        raise self.retry(exc=e)

    finally:
        db.close()


@celery_app.task(bind=True)
def process_batch_documents_task(self, document_ids: List[int]) -> dict:
    """
    Process multiple documents in batch.

    Args:
        document_ids: List of document IDs to process

    Returns:
        Dictionary with batch results
    """
    logger.info(f"Processing batch of {len(document_ids)} documents")

    results = {
        "total": len(document_ids),
        "success": 0,
        "failed": 0,
        "details": [],
    }

    for doc_id in document_ids:
        try:
            result = process_document_task.delay(doc_id)
            results["details"].append({
                "document_id": doc_id,
                "task_id": result.id,
            })
        except Exception as e:
            logger.error(f"Failed to queue document {doc_id}: {e}")
            results["failed"] += 1
            results["details"].append({
                "document_id": doc_id,
                "error": str(e),
            })

    return results


@celery_app.task
def cleanup_failed_documents() -> dict:
    """
    Cleanup task to retry failed documents.

    Returns:
        Dictionary with cleanup results
    """
    logger.info("Running failed documents cleanup...")

    db = SessionLocal()
    try:
        failed_docs = db.query(Document).filter(
            Document.status == DocumentStatus.FAILED
        ).all()

        if not failed_docs:
            return {"status": "success", "message": "No failed documents found"}

        requeued = 0
        for doc in failed_docs:
            doc.status = DocumentStatus.PENDING
            doc.error_message = None
            process_document_task.delay(doc.id)
            requeued += 1

        db.commit()

        logger.info(f"Requeued {requeued} failed documents")

        return {
            "status": "success",
            "requeued": requeued,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Cleanup task error: {e}")
        return {"status": "error", "message": str(e)}

    finally:
        db.close()
