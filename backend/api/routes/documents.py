"""
Document upload/management routes (RAG source documents, /v1/documents).
"""
import logging
import uuid
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select, func

from config import settings
from core.auth import get_current_user
from database import get_database
from models import Document, SourceType, DocumentStatus, User
from models.chunk import Chunk

logger = logging.getLogger(__name__)
router = APIRouter(tags=["documents"])


@router.post("/v1/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    folder_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a document for RAG processing.

    Supported file types: PDF, DOCX, TXT, HTML, MD

    The document will be:
    1. Saved to storage
    2. Queued for background processing (parsing, chunking, embedding)

    Returns document ID and task ID for status tracking.
    """
    db = get_database()

    # Validate file type
    file_ext = Path(file.filename).suffix.lower().lstrip(".")
    if file_ext not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {settings.ALLOWED_FILE_TYPES}"
        )

    # Validate file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Seek back to start

    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    # Generate unique filename
    unique_id = str(uuid.uuid4())[:8]
    safe_filename = f"{unique_id}_{file.filename}"
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / safe_filename

    # Save file
    try:
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Create document record
    async with db.get_session() as session:
        document = Document(
            user_id=current_user.id,
            title=title.strip(),
            content="",  # Will be populated during processing
            source_type=SourceType.UPLOAD,
            file_path=str(file_path),
            file_type=file_ext,
            file_size=file_size,
            document_metadata={"original_filename": file.filename},
            status=DocumentStatus.PENDING,
        )
        session.add(document)
        await session.flush()
        document_id = document.id

    # Queue for background processing
    try:
        from tasks.ingestion_tasks import process_document_task
        task = process_document_task.delay(document_id)
        task_id = task.id
    except Exception as e:
        logger.warning(f"Celery not available, document will need manual processing: {e}")
        task_id = None

    return {
        "document_id": document_id,
        "task_id": task_id,
        "message": "Document uploaded and queued for processing",
        "filename": file.filename,
        "file_type": file_ext,
        "file_size": file_size,
    }


@router.get("/v1/documents")
async def list_documents(
    status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
):
    """List all documents for the current user"""
    db = get_database()
    async with db.get_session() as session:
        query = select(Document).where(
            Document.user_id == current_user.id,
            Document.is_deleted == False
        )

        if status:
            try:
                status_enum = DocumentStatus(status)
                query = query.where(Document.status == status_enum)
            except ValueError:
                pass

        if source_type:
            try:
                source_enum = SourceType(source_type)
                query = query.where(Document.source_type == source_enum)
            except ValueError:
                pass

        query = query.order_by(Document.created_at.desc()).limit(limit).offset(offset)
        result = await session.execute(query)
        documents = result.scalars().all()

        return {
            "documents": [doc.to_dict() for doc in documents],
            "total": len(documents),
        }


@router.get("/v1/documents/{document_id}")
async def get_document(document_id: int, current_user: User = Depends(get_current_user)):
    """Get a specific document with its chunks"""
    db = get_database()
    async with db.get_session() as session:
        # Get document
        result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document or document.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get chunks
        chunks_result = await session.execute(
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
        )
        chunks = chunks_result.scalars().all()

        return {
            "document": document.to_dict(),
            "chunks": [chunk.to_dict() for chunk in chunks],
        }


@router.get("/v1/documents/{document_id}/status")
async def get_document_status(document_id: int, current_user: User = Depends(get_current_user)):
    """Get processing status for a document"""
    db = get_database()
    async with db.get_session() as session:
        result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document or document.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Document not found")

        # Count chunks asynchronously (avoid sync relationship access in async context)
        chunk_count_result = await session.execute(
            select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id)
        )
        chunk_count = chunk_count_result.scalar() or 0

        return {
            "document_id": document.id,
            "status": document.status.value,
            "error_message": document.error_message,
            "chunk_count": chunk_count,
        }


@router.delete("/v1/documents/{document_id}")
async def delete_document(document_id: int, permanent: bool = Query(False), current_user: User = Depends(get_current_user)):
    """Delete a document (soft delete by default)"""
    db = get_database()
    async with db.get_session() as session:
        result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document or document.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Document not found")

        if permanent:
            # Delete file if exists
            if document.file_path:
                try:
                    Path(document.file_path).unlink(missing_ok=True)
                except Exception:
                    pass
            await session.delete(document)
        else:
            document.is_deleted = True

        await session.commit()

    return {"message": "Document deleted" if permanent else "Document moved to trash"}
