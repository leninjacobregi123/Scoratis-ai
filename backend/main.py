"""
Scoratis FastAPI Backend
High-performance async API for the learning platform
Multi-LLM support with adaptive learning prompts
RAG + Web Search augmentation for enhanced responses
"""

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
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
from llm_service import llm_service, RECOMMENDED_MODELS
from prompts import (
    detect_video_potential, get_subject_prompt, get_available_subjects,
    SUBJECT_CHANNELS, CITATION_INSTRUCTIONS, RAG_CONTEXT_AWARENESS
)
from models import ProviderType, PROVIDER_INFO, LLMProviderConfig, Document, SourceType, DocumentStatus
from services.encryption_service import get_encryption_service
from video_service import video_service
from conversation_analyzer import conversation_analyzer, VideoTrigger
from coqui_tts_service import coqui_tts_service, TUTOR_VOICES
from services import get_rag_service, get_web_search_service, get_memory_service
from services.langgraph_service import initialize_langgraph_service, get_langgraph_service
from services.video_analyzer_service import (
    VideoAnalyzerService,
    init_video_analyzer_service,
    get_video_analyzer_service
)
from services.agent import create_agent, get_agent, ScoratisAgent
from config import settings

load_dotenv()
logger = logging.getLogger(__name__)

# Pydantic Models
class JournalCreate(BaseModel):
    title: str
    content: str
    tags: Optional[List[str]] = []
    folder_id: Optional[int] = None

class JournalUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    folder_id: Optional[int] = None

class FolderCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    color: Optional[str] = "#8A2BE2"

class FolderUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    subject: Optional[str] = "general"  # Subject channel: physics, chemistry, math, etc.

class DeleteConversation(BaseModel):
    permanent: Optional[bool] = False

class ConversationUpdate(BaseModel):
    title: Optional[str] = None

class LLMConfigUpdate(BaseModel):
    model: str
    provider: Optional[str] = "ollama"
    base_url: Optional[str] = None
    max_tokens: Optional[int] = 2048
    temperature: Optional[float] = 0.7
    context_length: Optional[int] = 4096


class LLMProviderCreate(BaseModel):
    """Create a new LLM provider configuration"""
    provider: str  # ollama, openai, anthropic, google, groq, together, azure
    name: str
    api_key: Optional[str] = None  # Will be encrypted before storage
    base_url: Optional[str] = None
    is_default: Optional[bool] = False


class LLMProviderUpdate(BaseModel):
    """Update an existing LLM provider configuration"""
    name: Optional[str] = None
    api_key: Optional[str] = None  # Will be encrypted before storage
    base_url: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class SessionModelUpdate(BaseModel):
    """Update the model for a specific session"""
    session_id: str
    provider_id: Optional[int] = None
    model: str

class VideoGenerateRequest(BaseModel):
    topic: str
    quality: Optional[str] = "high"
    duration: Optional[int] = 90

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global db, rag_service, web_search_service, memory_service, langgraph_service, video_analyzer_service, scoratis_agent

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

    print("Scoratis FastAPI Server Started (PostgreSQL + RAG + Web Search + LangGraph + Agent + Auto-Video)")
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
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for generated videos
GENERATED_VIDEOS_DIR = Path(__file__).parent / "generated_videos"
GENERATED_VIDEOS_DIR.mkdir(exist_ok=True)
app.mount("/generated_videos", StaticFiles(directory=str(GENERATED_VIDEOS_DIR)), name="generated_videos")

# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    stats = await db.get_user_stats()
    return {
        "status": "running",
        "message": "Scoratis FastAPI is healthy",
        "version": "3.0",
        "database": "PostgreSQL + pgvector",
        "features": ["RAG", "Web Search", "Embeddings"],
        "stats": stats
    }

@app.get("/stats")
async def get_stats():
    """Get user statistics"""
    return await db.get_user_stats()


@app.get("/migrations/status")
async def get_migration_status():
    """Get database migration status (Alembic)"""
    return db.get_migration_status()


# ==================== JOURNAL ENDPOINTS ====================

@app.get("/journals")
async def get_journals(
    folder_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None)
):
    """Get all journals with optional filtering"""
    return await db.get_journals(folder_id=folder_id, search_query=search)

@app.post("/journals", status_code=201)
async def create_journal(journal: JournalCreate):
    """Create a new journal entry with embedding for RAG"""
    if not journal.title.strip() or not journal.content.strip():
        raise HTTPException(status_code=400, detail="Title and content are required")

    journal_id = await db.create_journal(
        title=journal.title.strip(),
        content=journal.content.strip(),
        tags=journal.tags,
        folder_id=journal.folder_id
    )
    return {"id": journal_id, "message": "Journal created successfully"}

@app.put("/journals/{journal_id}")
async def update_journal(journal_id: int, journal: JournalUpdate):
    """Update a journal entry (re-generates embedding)"""
    success = await db.update_journal(
        journal_id,
        title=journal.title,
        content=journal.content,
        tags=journal.tags,
        folder_id=journal.folder_id
    )
    if not success:
        raise HTTPException(status_code=400, detail="No changes made")
    return {"message": "Journal updated successfully"}

@app.delete("/journals/{journal_id}")
async def delete_journal(journal_id: int):
    """Delete a journal entry"""
    await db.delete_journal(journal_id)
    return {"message": "Journal deleted successfully"}

# ==================== FOLDER ENDPOINTS ====================

@app.get("/folders")
async def get_folders():
    """Get all folders"""
    return await db.get_folders()

@app.post("/folders", status_code=201)
async def create_folder(folder: FolderCreate):
    """Create a new folder"""
    if not folder.name.strip():
        raise HTTPException(status_code=400, detail="Folder name is required")

    folder_id = await db.create_folder(
        name=folder.name.strip(),
        description=folder.description.strip() if folder.description else "",
        color=folder.color
    )
    return {"id": folder_id, "message": "Folder created successfully"}

@app.put("/folders/{folder_id}")
async def update_folder(folder_id: int, folder: FolderUpdate):
    """Update a folder"""
    success = await db.update_folder(
        folder_id,
        name=folder.name,
        description=folder.description,
        color=folder.color
    )
    if not success:
        raise HTTPException(status_code=400, detail="No changes made")
    return {"message": "Folder updated successfully"}

@app.delete("/folders/{folder_id}")
async def delete_folder(folder_id: int):
    """Delete a folder"""
    await db.delete_folder(folder_id)
    return {"message": "Folder deleted successfully"}

# ==================== CHAT ENDPOINTS ====================

def generate_fallback(user_message: str) -> str:
    """Generate contextual fallback response when no LLM is available"""
    msg_lower = user_message.lower().strip()

    if any(word in msg_lower for word in ["everything", "nothing", "all of it"]):
        return "Feeling overwhelmed? Let's start with something tiny and concrete. What's one specific thing you'd like to understand better? We'll take it step by step!"

    if any(phrase in msg_lower for phrase in ["don't know", "dont know", "idk", "confused"]):
        return "That's completely normal when learning something new! Confusion is actually the first step to understanding. Can you tell me what part feels most unclear? We'll tackle it together."

    if any(phrase in msg_lower for phrase in ["teach me", "learn", "start"]):
        return "I'd love to help you learn! To give you the best guidance, could you tell me: What topic are you interested in? And what do you already know about it (even if it's just a little)?"

    if any(phrase in msg_lower for phrase in ["help", "homework", "assignment"]):
        return "I'm here to help! Let's work through this together. What's the specific problem or question you're working on? Share it with me and we'll break it down step by step."

    return f"Great question! I want to make sure I give you the most helpful response. Could you tell me a bit more about what you're trying to learn or accomplish? That way I can tailor my explanation to exactly what you need."

# ==================== LLM CONFIGURATION ENDPOINTS ====================

@app.get("/llm/providers")
async def get_llm_providers():
    """Get available LLM providers and their models"""
    availability = await llm_service.check_availability()
    models = llm_service.get_available_models()
    current = llm_service.get_current_config()
    recommended = llm_service.get_recommended_models(vram_gb=4)  # GTX 1650 = 4GB

    return {
        "availability": availability,
        "models": models,
        "current": current,
        "recommended": recommended,
        "vram_tiers": RECOMMENDED_MODELS
    }

@app.post("/llm/configure")
async def configure_llm(config: LLMConfigUpdate):
    """Configure the LLM model"""
    try:
        llm_service.set_provider(
            model=config.model,
            provider=config.provider or "ollama",
            base_url=config.base_url,
            max_tokens=config.max_tokens or 2048,
            temperature=config.temperature or 0.7,
            context_length=config.context_length or 4096
        )
        return {
            "message": f"LLM configured to {config.provider or 'ollama'}/{config.model}",
            "config": llm_service.get_current_config()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/llm/test")
async def test_llm():
    """Test the current LLM configuration"""
    try:
        response = await llm_service.generate(
            messages=[{"role": "user", "content": "Say 'Hello, I am working!' in exactly those words."}],
            system_prompt="You are a helpful assistant. Respond exactly as instructed."
        )
        return {
            "status": "success",
            "response": response,
            "config": llm_service.get_current_config()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "config": llm_service.get_current_config()
        }

@app.get("/llm/health")
async def llm_health():
    """Comprehensive LLM health check"""
    return await llm_service.health_check()

@app.get("/llm/recommended")
async def get_recommended_models(vram_gb: int = Query(4, description="GPU VRAM in GB")):
    """Get recommended models for your hardware"""
    return {
        "vram_gb": vram_gb,
        "recommended": llm_service.get_recommended_models(vram_gb)
    }


# ==================== LLM PROVIDER MANAGEMENT ENDPOINTS ====================

@app.get("/llm/providers/available")
async def get_available_llm_providers():
    """Get all available LLM providers with their models"""
    providers = llm_service.get_available_providers()
    return {
        "providers": providers,
        "total": len(providers)
    }


@app.get("/llm/providers/configured")
async def get_configured_providers():
    """Get all configured LLM provider configurations from database"""
    async with db.get_session() as session:
        from sqlalchemy import select
        from models import LLMProviderConfig

        stmt = select(LLMProviderConfig).where(LLMProviderConfig.user_id == 1)
        result = await session.execute(stmt)
        configs = result.scalars().all()

        encryption = get_encryption_service()
        return {
            "providers": [
                {
                    **config.to_dict(),
                    "api_key_masked": encryption.mask_key(
                        encryption.decrypt(config.api_key_encrypted)
                    ) if config.api_key_encrypted else None
                }
                for config in configs
            ]
        }


@app.post("/llm/providers/configured", status_code=201)
async def create_provider_config(provider_config: LLMProviderCreate):
    """Create a new LLM provider configuration with encrypted API key"""
    try:
        provider_type = ProviderType(provider_config.provider.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider_config.provider}")

    encryption = get_encryption_service()

    async with db.get_session() as session:
        from models import LLMProviderConfig

        # If setting as default, unset other defaults
        if provider_config.is_default:
            from sqlalchemy import update
            await session.execute(
                update(LLMProviderConfig)
                .where(LLMProviderConfig.user_id == 1)
                .values(is_default=False)
            )

        # Encrypt API key if provided
        encrypted_key = None
        if provider_config.api_key:
            encrypted_key = encryption.encrypt(provider_config.api_key)

        new_config = LLMProviderConfig(
            user_id=1,
            provider=provider_type,
            name=provider_config.name,
            api_key_encrypted=encrypted_key,
            base_url=provider_config.base_url or PROVIDER_INFO.get(provider_type, {}).get("default_base_url"),
            is_active=True,
            is_default=provider_config.is_default or False,
        )

        session.add(new_config)
        await session.flush()

        return {
            "id": new_config.id,
            "message": f"Provider {provider_config.name} configured successfully",
            "provider": new_config.to_dict()
        }


@app.put("/llm/providers/configured/{provider_id}")
async def update_provider_config(provider_id: int, update_data: LLMProviderUpdate):
    """Update an existing LLM provider configuration"""
    encryption = get_encryption_service()

    async with db.get_session() as session:
        from models import LLMProviderConfig

        config = await session.get(LLMProviderConfig, provider_id)
        if not config:
            raise HTTPException(status_code=404, detail="Provider configuration not found")

        # If setting as default, unset other defaults
        if update_data.is_default:
            from sqlalchemy import update
            await session.execute(
                update(LLMProviderConfig)
                .where(LLMProviderConfig.user_id == 1)
                .where(LLMProviderConfig.id != provider_id)
                .values(is_default=False)
            )

        if update_data.name is not None:
            config.name = update_data.name
        if update_data.api_key is not None:
            config.api_key_encrypted = encryption.encrypt(update_data.api_key)
        if update_data.base_url is not None:
            config.base_url = update_data.base_url
        if update_data.is_active is not None:
            config.is_active = update_data.is_active
        if update_data.is_default is not None:
            config.is_default = update_data.is_default

        return {
            "message": "Provider configuration updated",
            "provider": config.to_dict()
        }


@app.delete("/llm/providers/configured/{provider_id}")
async def delete_provider_config(provider_id: int):
    """Delete an LLM provider configuration"""
    async with db.get_session() as session:
        from models import LLMProviderConfig

        config = await session.get(LLMProviderConfig, provider_id)
        if not config:
            raise HTTPException(status_code=404, detail="Provider configuration not found")

        await session.delete(config)
        return {"message": "Provider configuration deleted"}


@app.post("/llm/providers/{provider_id}/test")
async def test_provider_config(provider_id: int):
    """Test a configured provider by making a simple API call"""
    async with db.get_session() as session:
        from models import LLMProviderConfig

        config = await session.get(LLMProviderConfig, provider_id)
        if not config:
            raise HTTPException(status_code=404, detail="Provider configuration not found")

        provider_info = PROVIDER_INFO.get(config.provider, {})
        default_model = provider_info.get("models", [""])[0] if provider_info.get("models") else ""

        result = await llm_service.test_provider(
            provider=config.provider.value if isinstance(config.provider, ProviderType) else config.provider,
            model=default_model,
            api_key_encrypted=config.api_key_encrypted,
            base_url=config.base_url,
        )

        return {
            "provider_id": provider_id,
            "provider": config.provider.value if isinstance(config.provider, ProviderType) else config.provider,
            "model_tested": default_model,
            **result
        }


@app.post("/llm/session/model")
async def set_session_model(update: SessionModelUpdate):
    """Set the LLM model for a specific chat session"""
    encryption = get_encryption_service()

    # If provider_id is specified, get the configuration
    api_key_encrypted = None
    base_url = None
    provider = "ollama"

    if update.provider_id:
        async with db.get_session() as session:
            from models import LLMProviderConfig

            config = await session.get(LLMProviderConfig, update.provider_id)
            if not config:
                raise HTTPException(status_code=404, detail="Provider configuration not found")

            api_key_encrypted = config.api_key_encrypted
            base_url = config.base_url
            provider = config.provider.value if isinstance(config.provider, ProviderType) else config.provider

    # Store the session model preference (in-memory for now)
    session_id = update.session_id
    if session_id not in conversation_memory:
        conversation_memory[session_id] = []

    # Update the global LLM service for this request
    llm_service.set_provider(
        model=update.model,
        provider=provider,
        base_url=base_url,
        api_key_encrypted=api_key_encrypted,
    )

    return {
        "message": f"Session {session_id} now using {provider}/{update.model}",
        "session_id": session_id,
        "provider": provider,
        "model": update.model
    }


@app.get("/llm/available-models")
async def get_all_available_models():
    """Get all available models grouped by provider"""
    models = llm_service.get_available_models()

    # Also check Ollama for installed models
    ollama_health = await llm_service.litellm.check_ollama_health()

    return {
        "models": models,
        "ollama_installed": ollama_health.get("installed_models", []),
        "ollama_available": ollama_health.get("available", False)
    }


# ==================== SUBJECT CHANNELS ENDPOINTS ====================

@app.get("/subjects")
async def get_subjects():
    """Get available subject channels for the Gallery"""
    subjects = get_available_subjects()
    # Convert to list format for frontend
    subjects_list = list(subjects.values())
    return {
        "subjects": subjects_list,
        "total": len(subjects_list)
    }

@app.get("/subjects/{subject_id}")
async def get_subject(subject_id: str):
    """Get details for a specific subject"""
    subjects = get_available_subjects()
    if subject_id not in subjects:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")
    return subjects[subject_id]

# ==================== CHAT ENDPOINTS ====================

@app.get("/chat/tutor-voices")
async def get_tutor_voices():
    """Get available voices for each tutor mode"""
    return {
        "voices": coqui_tts_service.get_available_voices(),
        "default": "socrates"
    }

class TTSRequest(BaseModel):
    text: str

@app.post("/chat/tts")
async def generate_tts(request: TTSRequest):
    """Generate TTS audio for a chat message (using Coqui TTS or Edge TTS fallback)"""
    if not request.text or len(request.text.strip()) < 2:
        raise HTTPException(status_code=400, detail="Text too short for TTS")

    audio_path = coqui_tts_service.synthesize(
        text=request.text,
        tutor_mode="socrates"  # Always use Socratic voice
    )

    if audio_path and audio_path.exists():
        # Determine media type based on file extension
        ext = audio_path.suffix.lower()
        if ext == '.mp3':
            media_type = "audio/mpeg"
        elif ext == '.wav':
            media_type = "audio/wav"
        else:
            media_type = "audio/mpeg"  # Default to MP3

        return FileResponse(
            path=str(audio_path),
            media_type=media_type,
            filename=f"response_{audio_path.stem}{ext}"
        )

    raise HTTPException(status_code=500, detail="TTS generation failed")

@app.post("/chat")
async def chat(message: ChatMessage):
    """Chat with Scoratis AI assistant using RAG + Web Search augmentation"""
    user_message = message.message.strip()
    session_id = message.session_id

    if not user_message:
        raise HTTPException(status_code=400, detail="No message provided")

    # Get subject (defaults to "general")
    subject = message.subject or "general"

    # Get subject-specific prompt (all subjects use Socratic + scaffolding approach)
    base_system_prompt = get_subject_prompt(subject)
    context = subject

    try:
        # Get or initialize conversation history
        if session_id not in conversation_memory:
            conversation_memory[session_id] = []

        # Save user message to database with embedding
        conversation_id = await db.add_chat_message(session_id, 'user', user_message)

        # Add to memory service
        memory_service.add_message(session_id, "user", user_message)

        # Add to local memory
        conversation_memory[session_id].append({
            "role": "user",
            "content": user_message
        })

        # Keep only last 10 message pairs (20 messages)
        if len(conversation_memory[session_id]) > 20:
            conversation_memory[session_id] = conversation_memory[session_id][-20:]

        # === RAG: Get relevant context from journals and past conversations ===
        rag_context = ""
        search_used = False
        try:
            async with db.get_session() as db_session:
                relevant_context = await rag_service.get_relevant_context(
                    db_session, user_message, session_id
                )
                rag_context = rag_service.format_context_for_llm(relevant_context)
                if rag_context:
                    logger.info(f"RAG context found: {len(relevant_context.get('journals', []))} journals, {len(relevant_context.get('conversations', []))} past messages")
        except Exception as rag_error:
            logger.warning(f"RAG search error (continuing without): {rag_error}")

        # Build enhanced system prompt with RAG context
        if rag_context:
            system_prompt = f"{base_system_prompt}\n\n---\nRELEVANT CONTEXT FROM USER'S NOTES AND PAST DISCUSSIONS:\n{rag_context}\n---\nUse the above context to provide more personalized and relevant responses."
        else:
            system_prompt = base_system_prompt

        # Generate response using LLM service
        try:
            response_text = await llm_service.generate(
                messages=conversation_memory[session_id],
                system_prompt=system_prompt
            )
            source = "llm"

            # === Web Search: Check for knowledge gaps and augment if needed ===
            if settings.WEB_SEARCH_ENABLED:
                try:
                    augmentation = await web_search_service.augment_response(
                        user_message, response_text
                    )
                    if augmentation:
                        logger.info(f"Knowledge gap detected, performing web search for: {augmentation['query']}")
                        search_used = True

                        # Re-generate with search context
                        search_prompt = f"{system_prompt}\n\n{augmentation['formatted_context']}"
                        response_text = await llm_service.generate(
                            messages=conversation_memory[session_id],
                            system_prompt=search_prompt
                        )
                        source = "llm+search"
                except Exception as search_error:
                    logger.warning(f"Web search error (using original response): {search_error}")

        except Exception as llm_error:
            logger.error(f"LLM Error: {llm_error}")
            response_text = generate_fallback(user_message)
            source = "fallback"

        # Save AI response to database with embedding
        await db.add_chat_message(session_id, 'ai', response_text)

        # Add to memory service
        memory_service.add_message(session_id, "assistant", response_text)

        # Add to local memory
        conversation_memory[session_id].append({
            "role": "assistant",
            "content": response_text
        })

        # Get current LLM info
        current_config = llm_service.get_current_config()

        # === LangGraph Video Analysis ===
        # Use LLM-based analysis to determine if content is suitable for video
        video_available = False
        video_topic = None
        video_concepts = []
        video_type = None
        learning_state_str = "initial"
        turn_count = 0

        try:
            if langgraph_service:
                # Use LangGraph for intelligent video analysis (analysis only, no LLM call)
                lg_result = await langgraph_service.analyze_for_video(
                    session_id=session_id,
                    user_message=user_message,
                    ai_response=response_text,
                    subject=subject
                )
                video_available = lg_result.get("video_available", False)
                video_topic = lg_result.get("video_topic")
                video_concepts = lg_result.get("video_concepts", [])
                video_type = lg_result.get("video_type")
                learning_state_str = lg_result.get("learning_state", "initial")
                turn_count = lg_result.get("turn_count", 0)
            else:
                # Fallback to conversation analyzer
                video_analysis = conversation_analyzer.analyze_message(
                    session_id=session_id,
                    user_message=user_message,
                    ai_response=response_text
                )
                video_available = video_analysis.get('should_offer_video', False)
                video_topic = video_analysis.get('suggested_video_topic')
                learning_state_str = video_analysis.get('learning_state', 'initial')
                turn_count = video_analysis.get('turn_count', 0)
        except Exception as video_err:
            logger.warning(f"Video analysis error (continuing without): {video_err}")

        return {
            "reply": response_text,
            "source": source,
            "search_used": search_used,
            "session_id": session_id,
            "context": context,
            "conversation_id": conversation_id,
            "model": current_config.get("model") if current_config else None,
            # New video fields for user-triggered generation
            "video_available": video_available,
            "video_topic": video_topic,
            "video_concepts": video_concepts,
            "video_type": video_type,
            "learning_state": learning_state_str,
            "turn_count": turn_count
        }

    except Exception as e:
        logger.error(f"Chat Error: {e}")
        response_text = generate_fallback(user_message)
        try:
            await db.add_chat_message(session_id, 'ai', response_text)
        except:
            pass
        return {
            "reply": response_text,
            "source": "fallback",
            "session_id": session_id,
            "error": str(e),
            "search_used": False,
            "video_available": False,
            "video_topic": None,
            "video_concepts": [],
            "video_type": None,
            "learning_state": "initial",
            "turn_count": 0
        }

@app.post("/chat/stream")
async def chat_stream(message: ChatMessage):
    """Stream chat responses from Scoratis AI with RAG + Web Search"""
    user_message = message.message.strip()
    session_id = message.session_id

    if not user_message:
        raise HTTPException(status_code=400, detail="No message provided")

    # Get subject (defaults to "general")
    subject = message.subject or "general"

    # Get subject-specific prompt
    base_system_prompt = get_subject_prompt(subject)
    context = subject

    # Get or initialize conversation history
    if session_id not in conversation_memory:
        conversation_memory[session_id] = []

    # Save user message to database with embedding
    conversation_id = await db.add_chat_message(session_id, 'user', user_message)

    # Add to memory service
    memory_service.add_message(session_id, "user", user_message)

    # Add to local memory
    conversation_memory[session_id].append({
        "role": "user",
        "content": user_message
    })

    # Keep only last 10 message pairs (20 messages)
    if len(conversation_memory[session_id]) > 20:
        conversation_memory[session_id] = conversation_memory[session_id][-20:]

    # === RAG: Get relevant context with hybrid search ===
    rag_context_xml = ""
    rag_sources = []
    rag_chunk_mapping = {}

    try:
        async with db.get_session() as db_session:
            # Try new hybrid search with citations first
            try:
                rag_result = await rag_service.get_context_with_citations(
                    db_session, user_message
                )
                rag_context_xml = rag_result.get("context_xml", "")
                rag_sources = rag_result.get("sources", [])
                rag_chunk_mapping = rag_result.get("chunk_mapping", {})
            except Exception as hybrid_error:
                logger.warning(f"Hybrid search error, falling back to legacy: {hybrid_error}")
                # Fallback to legacy search
                relevant_context = await rag_service.get_relevant_context(
                    db_session, user_message, session_id
                )
                rag_context_xml = rag_service.format_context_for_llm(relevant_context)
    except Exception as rag_error:
        logger.warning(f"RAG search error (continuing without): {rag_error}")

    # Build enhanced system prompt with citation instructions
    if rag_context_xml and rag_sources:
        system_prompt = f"""{base_system_prompt}

{RAG_CONTEXT_AWARENESS}

{CITATION_INSTRUCTIONS}

---
{rag_context_xml}
---"""
    elif rag_context_xml:
        # Legacy context (no citations)
        system_prompt = f"{base_system_prompt}\n\n---\nRELEVANT CONTEXT:\n{rag_context_xml}\n---"
    else:
        system_prompt = base_system_prompt

    async def generate_stream():
        full_response = ""
        search_used = False
        try:
            # Stream sources BEFORE LLM response (for citation preview)
            if rag_sources:
                sources_event = {
                    "type": "sources",
                    "sources": [
                        {
                            "chunk_id": src.get("chunk_id"),
                            "citation_number": src.get("citation_number"),
                            "document_id": src.get("document_id"),
                            "document_title": src.get("document_title"),
                            "content_preview": src.get("content_preview", "")[:200],
                            "content": src.get("content", "")[:500],
                            "page": src.get("page"),
                            "source_type": src.get("source_type"),
                        }
                        for src in rag_sources[:10]  # Limit to top 10 sources
                    ]
                }
                yield f"data: {json.dumps(sources_event)}\n\n"

            # Stream the response
            async for chunk in llm_service.generate_stream(
                messages=conversation_memory[session_id],
                system_prompt=system_prompt
            ):
                full_response += chunk
                yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"

            # Save complete response to database with embedding
            await db.add_chat_message(session_id, 'ai', full_response)

            # Add to memory service
            memory_service.add_message(session_id, "assistant", full_response)

            # Add to local memory
            conversation_memory[session_id].append({
                "role": "assistant",
                "content": full_response
            })

            # Get current LLM info
            current_config = llm_service.get_current_config()

            # === Automatic Video Generation Analysis ===
            video_available = False
            video_topic = None
            video_concepts = []
            video_type = None
            learning_state_str = "initial"
            turn_count = 0
            auto_video_info = None  # NEW: For automatic video generation

            try:
                # First, get turn count from LangGraph or conversation analyzer
                lg_result = None  # Initialize for later use
                if langgraph_service:
                    lg_result = await langgraph_service.analyze_for_video(
                        session_id=session_id,
                        user_message=user_message,
                        ai_response=full_response,
                        subject=subject
                    )
                    learning_state_str = lg_result.get("learning_state", "initial")
                    turn_count = lg_result.get("turn_count", 0)
                else:
                    video_analysis = conversation_analyzer.analyze_message(
                        session_id=session_id,
                        user_message=user_message,
                        ai_response=full_response
                    )
                    learning_state_str = video_analysis.get('learning_state', 'initial')
                    turn_count = video_analysis.get('turn_count', 0)

                # === NEW: Automatic Video Generation Decision ===
                video_analyzer = get_video_analyzer_service()
                if video_analyzer:
                    decision = await video_analyzer.should_auto_generate(
                        session_id=session_id,
                        user_message=user_message,
                        ai_response=full_response,
                        subject=subject,
                        turn_count=turn_count
                    )

                    if decision.should_generate:
                        # Build context for video generation
                        video_context = {
                            "topic_title": decision.topic,
                            "key_concepts": decision.key_concepts,
                            "visualization_type": decision.visualization_type,
                            "duration_suggestion": decision.duration_seconds,
                            "learning_state": learning_state_str,
                            "conversation_summary": user_message[:200] + "..." if len(user_message) > 200 else user_message
                        }

                        # Start video generation in background
                        task_id = await video_service.start_generation(
                            topic=decision.topic,
                            quality="high",
                            duration=decision.duration_seconds,
                            context=video_context,
                            auto_generated=True
                        )

                        # Record this generation for cooldown tracking
                        video_analyzer.record_video_generation(session_id, turn_count)

                        # Build auto_video info for frontend
                        auto_video_info = {
                            "task_id": task_id,
                            "topic": decision.topic,
                            "concepts": decision.key_concepts,
                            "visualization_type": decision.visualization_type,
                            "estimated_duration": decision.duration_seconds,
                            "confidence": decision.confidence
                        }

                        logger.info(f"Auto-generating video: {decision.topic} (confidence: {decision.confidence:.2f})")

                        # Also set video_available for fallback UI
                        video_available = True
                        video_topic = decision.topic
                        video_concepts = decision.key_concepts
                        video_type = decision.visualization_type
                    else:
                        # No auto-generation, but still check if we should offer manual option
                        # Use the existing LangGraph/conversation analyzer results
                        if langgraph_service and lg_result:
                            video_available = lg_result.get("video_available", False)
                            video_topic = lg_result.get("video_topic")
                            video_concepts = lg_result.get("video_concepts", [])
                            video_type = lg_result.get("video_type")

            except Exception as video_err:
                logger.warning(f"Video analysis/generation error: {video_err}")

            final_data = {
                'chunk': '',
                'done': True,
                'full_response': full_response,
                'context': context,
                'conversation_id': conversation_id,
                'model': current_config.get('model') if current_config else None,
                'search_used': search_used,
                # Existing video offer fields (for fallback/manual UI)
                'video_available': video_available,
                'video_topic': video_topic,
                'video_concepts': video_concepts,
                'video_type': video_type,
                'learning_state': learning_state_str,
                'turn_count': turn_count,
                # NEW: Automatic video generation info
                'auto_video': auto_video_info  # None if not auto-generating
            }
            yield f"data: {json.dumps(final_data)}\n\n"

        except Exception as e:
            logger.error(f"Stream Error: {e}")
            fallback = generate_fallback(user_message)
            error_data = {
                'chunk': fallback,
                'done': True,
                'error': str(e),
                'full_response': fallback,
                'search_used': False,
                'video_available': False,
                'video_topic': None,
                'video_concepts': [],
                'video_type': None,
                'learning_state': 'initial',
                'turn_count': 0,
                'auto_video': None  # No auto-video on error
            }
            yield f"data: {json.dumps(error_data)}\n\n"
            try:
                await db.add_chat_message(session_id, 'ai', fallback)
                conversation_memory[session_id].append({
                    "role": "assistant",
                    "content": fallback
                })
            except:
                pass

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/chat/clear")
async def clear_chat(session_id: str = "default"):
    """Clear conversation memory"""
    if session_id in conversation_memory:
        del conversation_memory[session_id]
    # Clear memory service
    memory_service.clear_session(session_id)
    # Reset conversation analyzer state
    conversation_analyzer.reset_session(session_id)
    # Clear from database
    await db.clear_conversation(session_id)
    return {"message": "Conversation cleared", "session_id": session_id}


@app.get("/chat/session/{session_id}/state")
async def get_session_state(session_id: str):
    """Get the learning state for a session"""
    state = conversation_analyzer.get_or_create_state(session_id)
    return state.to_dict()


@app.get("/chat/session/{session_id}/summary")
async def get_session_summary(session_id: str):
    """Get a summary of the learning session for recap"""
    summary = conversation_analyzer.get_session_summary(session_id)
    if not summary:
        return {"error": "Session not found", "session_id": session_id}
    return {
        "session_id": session_id,
        "summary": summary
    }


class GenerateVideoFromChatRequest(BaseModel):
    """Request model for user-triggered video generation"""
    session_id: str
    custom_topic: Optional[str] = None  # Override detected topic


@app.post("/chat/generate-video")
async def generate_video_from_chat(request: GenerateVideoFromChatRequest):
    """
    User-triggered video generation using LangGraph conversation context.
    Generates a 15-30 second focused educational video.

    This endpoint is called when user clicks the "Generate Video" button
    that appears after video_available=true in chat response.
    """
    session_id = request.session_id

    # Get video context from LangGraph service
    if not langgraph_service:
        raise HTTPException(
            status_code=503,
            detail="Video generation service not available"
        )

    try:
        video_context = await langgraph_service.get_video_context(session_id)

        if not video_context:
            raise HTTPException(
                status_code=400,
                detail="No visualizable content available for this session. Continue the conversation to build context."
            )

        # Use custom topic if provided, otherwise use detected topic
        topic = request.custom_topic or video_context.get("topic_title")

        if not topic:
            raise HTTPException(
                status_code=400,
                detail="No topic available for video generation"
            )

        # Build context for short, focused video (15-30 seconds)
        generation_context = {
            "topic_title": topic,
            "key_concepts": video_context.get("key_concepts", [])[:3],  # Limit for short video
            "visualization_hints": video_context.get("visualization_hints", [])[:2],
            "visualization_type": video_context.get("visualization_type"),
            "conversation_summary": video_context.get("conversation_summary", ""),
            "learning_state": video_context.get("learning_state"),
            "duration_suggestion": 20  # Target 20 seconds (15-30 range)
        }

        # Start video generation with short duration
        task_id = await video_service.start_generation(
            topic=topic,
            quality="high",
            duration=20,  # Short focused video
            context=generation_context
        )

        return {
            "task_id": task_id,
            "topic": topic,
            "concepts": video_context.get("key_concepts", [])[:3],
            "visualization_type": video_context.get("visualization_type"),
            "duration": "15-30 seconds",
            "message": "Video generation started. Poll /videos/status/{task_id} for progress."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class VideoTriggerRequest(BaseModel):
    session_id: str
    trigger_type: str  # 'scaffold', 'reinforcement', 'summary'
    topic: Optional[str] = None


class ContextAwareVideoRequest(BaseModel):
    session_id: str
    topic: Optional[str] = None
    use_context: Optional[bool] = True  # Use conversation context for Manim generation


@app.post("/chat/video/trigger")
async def trigger_video_generation(request: VideoTriggerRequest):
    """Manually trigger video generation based on learning context"""
    state = conversation_analyzer.get_or_create_state(request.session_id)

    # Determine topic
    topic = request.topic or state.topic
    if not topic:
        raise HTTPException(status_code=400, detail="No topic available for video generation")

    # Generate appropriate video title based on trigger type
    if request.trigger_type == "scaffold":
        video_topic = f"Visual Guide: {topic.title()}"
    elif request.trigger_type == "reinforcement":
        video_topic = f"Visualizing Your Discovery: {topic.title()}"
    elif request.trigger_type == "summary":
        video_topic = f"Lesson Summary: {topic.title()}"
    else:
        video_topic = topic.title()

    # Get conversation context for context-aware generation
    video_context = conversation_analyzer.get_video_generation_context(request.session_id)

    try:
        task_id = await video_service.start_generation(
            topic=video_topic,
            quality="high",
            context=video_context  # Pass context for LLM-based generation
        )

        # Mark video as generated in state
        state.video_generated = True

        return {
            "task_id": task_id,
            "topic": video_topic,
            "trigger_type": request.trigger_type,
            "message": "Video generation started",
            "context_used": video_context is not None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/video/context-aware")
async def context_aware_video_generation(request: ContextAwareVideoRequest):
    """
    Generate a video using conversation context for LLM-based Manim code generation.
    This endpoint analyzes the chat history to create relevant video content.
    """
    # Get the conversation context
    video_context = conversation_analyzer.get_video_generation_context(request.session_id)

    if not video_context:
        raise HTTPException(
            status_code=400,
            detail="Not enough meaningful content in conversation for video generation. Continue the discussion to build context."
        )

    # Determine topic from context or request
    topic = request.topic or video_context.get("topic_title") or video_context.get("main_topic")
    if not topic:
        raise HTTPException(status_code=400, detail="No topic detected in conversation")

    state = conversation_analyzer.get_or_create_state(request.session_id)

    try:
        task_id = await video_service.start_generation(
            topic=topic,
            quality="high",
            context=video_context if request.use_context else None
        )

        # Mark video as generated
        state.video_generated = True

        return {
            "task_id": task_id,
            "topic": topic,
            "message": "Context-aware video generation started",
            "context": {
                "content_richness": video_context.get("content_richness"),
                "content_score": video_context.get("content_score"),
                "concepts_detected": video_context.get("key_concepts", []),
                "visualization_hints": video_context.get("visualization_hints", [])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/video/context/{session_id}")
async def get_video_context(session_id: str):
    """Get the current video generation context for a session"""
    context = conversation_analyzer.get_video_generation_context(session_id)

    if not context:
        return {
            "has_context": False,
            "message": "Not enough meaningful content yet. Continue the conversation to build context."
        }

    return {
        "has_context": True,
        "context": context
    }

@app.get("/chat/history")
async def get_conversation_history(limit: int = Query(20, le=50)):
    """Get conversation history"""
    conversations = await db.get_conversations(limit=limit)
    return {"conversations": conversations}

@app.get("/chat/conversations")
async def get_all_conversations(limit: int = Query(50, le=100)):
    """Get all conversations for sidebar"""
    conversations = await db.get_conversations(limit=limit)
    return {"conversations": conversations}

@app.get("/chat/conversation/{conversation_id}")
async def get_conversation_messages(conversation_id: str):
    """Get messages for a conversation"""
    # Handle both integer IDs and session IDs
    try:
        conv_id = int(conversation_id)
        messages = await db.get_conversation_messages_by_id(conv_id)
    except ValueError:
        messages = await db.get_conversation_messages(conversation_id)
    return {"messages": messages, "conversation_id": conversation_id}

@app.put("/chat/conversation/{conversation_id}")
async def update_conversation(conversation_id: int, data: ConversationUpdate):
    """Update conversation (rename)"""
    if data.title:
        await db.update_conversation_title(conversation_id, data.title)
    return {"message": "Conversation updated"}

@app.delete("/chat/conversation/{conversation_id}")
async def delete_conversation(conversation_id: int, data: DeleteConversation = None):
    """Delete a conversation"""
    permanent = data.permanent if data else False
    await db.delete_conversation(conversation_id, permanent=permanent)
    return {"message": "Conversation deleted" if permanent else "Moved to trash"}

# RAG Search endpoint for debugging/testing
@app.get("/rag/search")
async def rag_search(q: str = Query(..., min_length=1)):
    """Test RAG semantic search"""
    async with db.get_session() as session:
        journals = await rag_service.search_journals(session, q)
        conversations = await rag_service.search_conversations(session, q)

    return {
        "query": q,
        "journals": [
            {"title": r.title, "similarity": r.similarity, "content": r.content[:200]}
            for r in journals
        ],
        "conversations": [
            {"similarity": r.similarity, "content": r.content[:200]}
            for r in conversations
        ]
    }


# ==================== DOCUMENT UPLOAD ENDPOINTS ====================

@app.post("/v1/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    folder_id: Optional[int] = Form(None),
):
    """
    Upload a document for RAG processing.

    Supported file types: PDF, DOCX, TXT, HTML, MD

    The document will be:
    1. Saved to storage
    2. Queued for background processing (parsing, chunking, embedding)

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

    # Create document record
    async with db.get_session() as session:
        document = Document(
            user_id=1,  # Default user
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


@app.get("/v1/documents")
async def list_documents(
    status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
):
    """List all documents for the current user"""
    async with db.get_session() as session:
        from sqlalchemy import select

        query = select(Document).where(
            Document.user_id == 1,
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
async def get_document(document_id: int):
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

        if not document:
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
async def get_document_status(document_id: int):
    """Get processing status for a document"""
    async with db.get_session() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return {
            "document_id": document.id,
            "status": document.status.value,
            "error_message": document.error_message,
            "chunk_count": document.chunks.count() if document.chunks else 0,
        }


@app.delete("/v1/documents/{document_id}")
async def delete_document(document_id: int, permanent: bool = Query(False)):
    """Delete a document (soft delete by default)"""
    async with db.get_session() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
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

@app.post("/videos/generate")
async def generate_video(request: VideoGenerateRequest):
    """Start video generation task"""
    if not request.topic.strip():
        raise HTTPException(status_code=400, detail="Topic is required")

    task_id = await video_service.start_generation(
        topic=request.topic.strip(),
        quality=request.quality or "high",
        duration=request.duration or 90
    )

    return {
        "task_id": task_id,
        "message": "Video generation started",
        "topic": request.topic
    }

@app.get("/videos/status/{task_id}")
async def get_generation_status(task_id: str):
    """Get status of a video generation task"""
    status = video_service.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return status

@app.get("/videos/generated")
async def get_generated_videos():
    """Get list of generated videos"""
    videos = video_service.get_generated_videos()
    return {"videos": videos}


# ==================== AGENTIC CHAT ENDPOINTS ====================
# These endpoints use the new Scoratis Agent for multi-step reasoning

class AgenticChatMessage(BaseModel):
    """Request model for agentic chat"""
    message: str
    session_id: str = "default"
    subject: Optional[str] = "general"


@app.post("/agent/chat")
async def agentic_chat(message: AgenticChatMessage):
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
                user_id=1  # Default user
            )

            # Extract response, ensuring it's never None or empty
            ai_response = result.get("response") or result.get("reply") or ""
            if not ai_response:
                ai_response = "I apologize, but I couldn't generate a response. Please try again."

            # Save to database
            await db.add_chat_message(message.session_id, 'user', message.message)
            await db.add_chat_message(message.session_id, 'ai', ai_response)

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
async def agentic_chat_stream(message: AgenticChatMessage):
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
        ))

    async def generate_agent_stream():
        full_response = ""
        try:
            async with db.get_session() as db_session:
                async for event in scoratis_agent.stream(
                    session_id=message.session_id,
                    message=message.message.strip(),
                    subject=message.subject or "general",
                    db_session=db_session,
                    user_id=1
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
                        await db.add_chat_message(message.session_id, 'user', message.message)
                        await db.add_chat_message(message.session_id, 'ai', final_response)

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
