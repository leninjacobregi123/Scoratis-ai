"""
Scoratis FastAPI Backend
High-performance async API for the learning platform
Multi-LLM support with adaptive learning prompts
RAG + Web Search augmentation for enhanced responses
"""

import re

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import asyncio
import aiofiles
import uuid
from pathlib import Path
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import logging

from database import get_database, DatabaseManager
from llm_service import llm_service
from services.litellm_service import LLMGenerationError, LLMError
from prompts import (
    detect_video_potential, get_subject_prompt,
    SUBJECT_CHANNELS, CITATION_INSTRUCTIONS, RAG_CONTEXT_AWARENESS
)
from models import ProviderType, PROVIDER_INFO, LLMProviderConfig, Document, SourceType, DocumentStatus, User
from services.encryption_service import get_encryption_service
from video_service import video_service
from conversation_analyzer import conversation_analyzer, VideoTrigger
from coqui_tts_service import coqui_tts_service, TUTOR_VOICES
from services import get_rag_service, get_web_search_service, get_memory_service
from services.citation_processor import get_citation_processor
from services.langgraph_service import initialize_langgraph_service, get_langgraph_service
from services.video_analyzer_service import (
    VideoAnalyzerService,
    init_video_analyzer_service,
    get_video_analyzer_service
)
from services.agent import create_agent, get_agent, ScoratisAgent
from services.guardrail_service import (
    get_guardrail_service, GuardrailService, GuardrailResult, GuardrailResponse
)
from config import settings
from core_pkg.auth import get_current_user
from api_pkg.routes.auth import router as auth_router
from api_pkg.routes.videos import router as videos_router
from api_pkg.routes.quizzes import router as quizzes_router
from api_pkg.routes.progress import router as progress_router
from api_pkg.routes.review import router as review_router
from api_pkg.routes.transcripts import router as transcripts_router
from api_pkg.routes.subjects import router as subjects_router
from api_pkg.routes.health import router as health_router
from api_pkg.routes.journals import router as journals_router
from api_pkg.routes.llm import router as llm_router
from api_pkg.routes.chat import router as chat_router, chat_stream
from api_pkg.schemas import ChatMessage
from services.video_job_service import start_video_job
from services import progress_service, review_service

load_dotenv()
logger = logging.getLogger(__name__)


# Pydantic Models

# Global state
db: DatabaseManager = None
youtube_client = None
conversation_memory = {}
rag_service = None
web_search_service = None
memory_service = None
langgraph_service = None
video_analyzer_service = None
scoratis_agent: ScoratisAgent = None
guardrail_service: GuardrailService = None

def get_youtube_client():
    """Lazy load YouTube API client"""
    global youtube_client
    if youtube_client is None:
        try:
            from googleapiclient.discovery import build
            api_key = os.getenv("YOUTUBE_API_KEY")
            if api_key:
                youtube_client = build('youtube', 'v3', developerKey=api_key)
        except ImportError:
            pass
    return youtube_client

INSECURE_DEFAULT_SECRETS = {
    "SCORATIS_ENCRYPTION_KEY": "scoratis-default-dev-key-change-in-production-32chars",
    "JWT_SECRET_KEY": "scoratis-default-dev-jwt-secret-change-in-production",
}


def _guard_against_insecure_production_secrets() -> None:
    """Refuse to boot in production with secrets still at their insecure
    dev defaults - a cheap guardrail, not a full security audit."""
    if settings.ENVIRONMENT != "production":
        return
    still_default = [
        name for name, default in INSECURE_DEFAULT_SECRETS.items()
        if getattr(settings, name) == default
    ]
    if still_default:
        raise RuntimeError(
            f"Refusing to start with ENVIRONMENT=production while these secrets are "
            f"still at their insecure default values: {', '.join(still_default)}. "
            f"Set real values via environment variables/secrets before deploying."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global db, rag_service, web_search_service, memory_service, langgraph_service, video_analyzer_service, scoratis_agent, guardrail_service

    _guard_against_insecure_production_secrets()

    # Initialize PostgreSQL database
    db = get_database()
    logger.info("PostgreSQL Database initialized")

    # Initialize RAG and Web Search services
    rag_service = get_rag_service()
    web_search_service = get_web_search_service()
    memory_service = get_memory_service()
    logger.info("RAG, Web Search, and Memory services initialized")

    # Initialize LangGraph service for video analysis
    try:
        langgraph_service = initialize_langgraph_service(
            database_url=settings.DATABASE_URL_ASYNC,
            llm_service=llm_service,
            rag_service=rag_service
        )
        await langgraph_service.initialize()
        logger.info("LangGraph service initialized for video analysis")
    except Exception as e:
        logger.warning(f"LangGraph initialization failed (video analysis will use fallback): {e}")

    # Initialize Video Analyzer Service for automatic video generation
    try:
        video_analyzer_service = init_video_analyzer_service(
            llm_service=llm_service,
            langgraph_service=langgraph_service
        )
        logger.info("Video Analyzer service initialized for auto-generation")
    except Exception as e:
        logger.warning(f"Video Analyzer initialization failed: {e}")

    # Initialize the Scoratis Agent (agentic workflow)
    try:
        scoratis_agent = create_agent(
            llm_service=llm_service,
            rag_service=rag_service,
            web_search_service=web_search_service,
            langgraph_service=langgraph_service,
            database_url=settings.DATABASE_URL_ASYNC
        )
        await scoratis_agent.initialize()
        logger.info("Scoratis Agent initialized with agentic workflow")
    except Exception as e:
        logger.warning(f"Scoratis Agent initialization failed (using fallback): {e}")

    # Initialize Guardrail Service for subject validation
    guardrail_service = get_guardrail_service(llm_service)
    logger.info("Guardrail service initialized for subject validation")

    print("Scoratis FastAPI Server Started (PostgreSQL + RAG + Web Search + LangGraph + Agent + Auto-Video + Guardrails)")
    yield
    print("Scoratis FastAPI Server Stopped")

# Create FastAPI app
app = FastAPI(
    title="Scoratis API",
    description="AI-Powered Learning & Journaling Platform",
    version="3.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for generated videos
GENERATED_VIDEOS_DIR = Path(__file__).parent / "generated_videos"
GENERATED_VIDEOS_DIR.mkdir(exist_ok=True)
app.mount("/generated_videos", StaticFiles(directory=str(GENERATED_VIDEOS_DIR)), name="generated_videos")

app.include_router(auth_router)
app.include_router(videos_router)
app.include_router(quizzes_router)
app.include_router(progress_router)
app.include_router(review_router)
app.include_router(transcripts_router)
app.include_router(subjects_router)
app.include_router(health_router)
app.include_router(journals_router)
app.include_router(llm_router)
app.include_router(chat_router)

# ==================== DOCUMENT UPLOAD ENDPOINTS ====================

@app.post("/v1/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    subject: str = Form(...),  # Required: subject for subject-isolated RAG
    folder_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a document for RAG processing with subject tagging.

    Supported file types: PDF, DOCX, TXT, HTML, MD

    The document will be:
    1. Saved to storage
    2. Tagged with subject for subject-isolated retrieval
    3. Queued for background processing (parsing, chunking, embedding)

    Returns document ID and task ID for status tracking.
    """
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

    # Create document record with subject tagging
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
            subject=subject.strip(),  # Tag with subject for subject-isolated RAG
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


@app.get("/v1/documents")
async def list_documents(
    status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
):
    """List all documents for the current user"""
    async with db.get_session() as session:
        from sqlalchemy import select

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


@app.get("/v1/documents/{document_id}")
async def get_document(document_id: int, current_user: User = Depends(get_current_user)):
    """Get a specific document with its chunks"""
    async with db.get_session() as session:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from models import Chunk

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


@app.get("/v1/documents/{document_id}/status")
async def get_document_status(document_id: int, current_user: User = Depends(get_current_user)):
    """Get processing status for a document"""
    async with db.get_session() as session:
        from sqlalchemy import select, func
        from models.chunk import Chunk

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


@app.delete("/v1/documents/{document_id}")
async def delete_document(document_id: int, permanent: bool = Query(False), current_user: User = Depends(get_current_user)):
    """Delete a document (soft delete by default)"""
    async with db.get_session() as session:
        from sqlalchemy import select

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
                except:
                    pass
            await session.delete(document)
        else:
            document.is_deleted = True

        await session.commit()

    return {"message": "Document deleted" if permanent else "Document moved to trash"}


# ==================== VIDEO ENDPOINTS ====================

def parse_youtube_duration(duration: str) -> str:
    """Parse YouTube duration format"""
    import re
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

@app.get("/videos/search")
async def search_videos(
    q: str = Query(..., min_length=1),
    max_results: int = Query(12, le=25)
):
    """Search for videos"""
    youtube = get_youtube_client()

    if not youtube:
        # Return sample videos
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

            # Add to history
            try:
                db.add_video_to_history(video_id, snippet['title'], snippet['channelTitle'],
                                       formatted_videos[-1]['thumbnail'], q)
            except:
                pass

        return {"videos": formatted_videos, "source": "youtube"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/videos/history")
async def get_video_history(limit: int = Query(50, le=100)):
    """Get video watch history"""
    return db.get_video_history(limit=limit)

# ==================== VIDEO GENERATION ENDPOINTS ====================

@app.get("/videos/detect-visuals")
async def detect_visuals(topic: str = Query(..., min_length=1)):
    """Detect what visual elements will be used for a topic"""
    visuals = video_service.detect_visuals(topic)
    return {"visuals": visuals, "topic": topic}

# NOTE: POST /videos/generate, GET /videos/status/{task_id}, GET /videos/generated
# now live in api_pkg/routes/videos.py (Celery-backed, replaces the old
# in-memory-tracked pipeline below this comment used to call into).


# ==================== AGENTIC CHAT ENDPOINTS ====================
# These endpoints use the new Scoratis Agent for multi-step reasoning

class AgenticChatMessage(BaseModel):
    """Request model for agentic chat"""
    message: str
    session_id: str = "default"
    subject: Optional[str] = "general"


@app.post("/agent/chat")
async def agentic_chat(message: AgenticChatMessage, current_user: User = Depends(get_current_user)):
    """
    Non-streaming agentic chat endpoint.

    This endpoint uses the Scoratis Agent which can:
    - Search the knowledge base (journals, documents)
    - Search past conversations
    - Perform web searches
    - Track learning progress
    - Use multi-step reasoning with tools

    Returns the final response along with tool usage info.
    """
    if not message.message.strip():
        raise HTTPException(status_code=400, detail="No message provided")

    if not scoratis_agent:
        raise HTTPException(
            status_code=503,
            detail="Agentic service not available. Using standard chat."
        )

    try:
        async with db.get_session() as db_session:
            result = await scoratis_agent.invoke(
                session_id=message.session_id,
                message=message.message.strip(),
                subject=message.subject or "general",
                db_session=db_session,
                user_id=current_user.id
            )

            # Extract response, ensuring it's never None or empty
            ai_response = result.get("response") or result.get("reply") or ""
            if not ai_response:
                ai_response = "I apologize, but I couldn't generate a response. Please try again."

            # Save to database
            await db.add_chat_message(message.session_id, 'user', message.message, user_id=current_user.id)
            await db.add_chat_message(message.session_id, 'ai', ai_response, user_id=current_user.id)

            return {
                "reply": ai_response,
                "session_id": message.session_id,
                "subject": message.subject,
                "sources": result.get("sources", []),
                "tools_used": result.get("tools_used", []),
                "model": result.get("model"),
                "mode": result.get("mode", "agent"),
                "video_analysis": result.get("video_analysis"),
                "video_eligible": result.get("video_eligible", False),
            }

    except Exception as e:
        logger.error(f"Agentic chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/chat/stream")
async def agentic_chat_stream(message: AgenticChatMessage, current_user: User = Depends(get_current_user)):
    """
    Streaming agentic chat endpoint.

    Streams events including:
    - sources: Retrieved knowledge base sources
    - tool_start: When a tool begins execution
    - tool_end: Tool execution results
    - token: Text chunks of the response
    - done: Final completion with metadata

    This provides a rich "chain of thought" experience showing
    how the agent reasons through complex questions.
    """
    if not message.message.strip():
        raise HTTPException(status_code=400, detail="No message provided")

    if not scoratis_agent:
        # Fallback to standard streaming
        return await chat_stream(ChatMessage(
            message=message.message,
            session_id=message.session_id,
            subject=message.subject
        ), current_user)

    async def generate_agent_stream():
        full_response = ""
        try:
            async with db.get_session() as db_session:
                async for event in scoratis_agent.stream(
                    session_id=message.session_id,
                    message=message.message.strip(),
                    subject=message.subject or "general",
                    db_session=db_session,
                    user_id=current_user.id
                ):
                    event_type = event.get("type")

                    if event_type == "sources":
                        # Stream sources for citation preview
                        yield f"data: {json.dumps(event)}\n\n"

                    elif event_type == "tool_start":
                        # Show tool execution starting (chain of thought UI)
                        yield f"data: {json.dumps({'type': 'tool', 'tool': event['tool'], 'status': 'start', 'args': event.get('args', {})})}\n\n"

                    elif event_type == "tool_end":
                        # Show tool execution result
                        yield f"data: {json.dumps({'type': 'tool', 'tool': event['tool'], 'status': 'end', 'result': event.get('result', {})})}\n\n"

                    elif event_type == "token":
                        # Stream response text
                        full_response += event.get("content", "")
                        yield f"data: {json.dumps({'chunk': event['content'], 'done': False})}\n\n"

                    elif event_type == "done":
                        # Ensure response is never empty for database
                        final_response = full_response.strip() if full_response else ""
                        if not final_response:
                            final_response = event.get("response") or "I apologize, but I couldn't generate a complete response."

                        # Save to database
                        await db.add_chat_message(message.session_id, 'user', message.message, user_id=current_user.id)
                        await db.add_chat_message(message.session_id, 'ai', final_response, user_id=current_user.id)

                        # Final event with metadata
                        final_data = {
                            'chunk': '',
                            'done': True,
                            'full_response': final_response,
                            'session_id': message.session_id,
                            'subject': message.subject,
                            'model': event.get('metadata', {}).get('model'),
                            'sources': event.get('metadata', {}).get('sources', []),
                            'tools_used': event.get('metadata', {}).get('tools_used', 0),
                            'mode': 'agent'
                        }
                        yield f"data: {json.dumps(final_data)}\n\n"

        except Exception as e:
            logger.error(f"Agent stream error: {e}")
            error_data = {
                'chunk': f"I apologize, but I encountered an error: {str(e)}",
                'done': True,
                'error': str(e)
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate_agent_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/agent/tools")
async def get_agent_tools():
    """
    Get list of available agent tools.

    Returns the tools the agent can use, their descriptions,
    and parameters. Useful for understanding agent capabilities.
    """
    from services.agent import TOOL_REGISTRY

    return {
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category.value,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "required": p.required
                    }
                    for p in tool.parameters
                ]
            }
            for tool in TOOL_REGISTRY
        ],
        "total": len(TOOL_REGISTRY)
    }


@app.get("/agent/status")
async def get_agent_status():
    """
    Get the status of the Scoratis Agent.

    Returns information about whether the agent is initialized
    and what capabilities are available.
    """
    agent = get_agent()

    return {
        "available": agent is not None,
        "initialized": agent._initialized if agent else False,
        "capabilities": {
            "rag_search": rag_service is not None,
            "web_search": web_search_service is not None,
            "memory_persistence": langgraph_service is not None,
            "tool_calling": True,
            "streaming": True
        },
        "mode": "langgraph" if agent and agent.checkpointer else "fallback"
    }


# Run with: uvicorn main:app --reload --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
