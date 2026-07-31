"""
Scoratis FastAPI Backend
High-performance async API for the learning platform
Multi-LLM support with adaptive learning prompts
RAG + Web Search augmentation for enhanced responses
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import logging

from database import get_database, DatabaseManager
from llm_service import llm_service
from services import get_rag_service, get_web_search_service, get_memory_service
from services.langgraph_service import initialize_langgraph_service
from services.video_analyzer_service import init_video_analyzer_service
from services.agent import create_agent, ScoratisAgent
from config import settings
from api.routes.auth import router as auth_router
from api.routes.videos import router as videos_router
from api.routes.quizzes import router as quizzes_router
from api.routes.review import router as review_router
from api.routes.transcripts import router as transcripts_router
from api.routes.health import router as health_router
from api.routes.journals import router as journals_router
from api.routes.llm import router as llm_router
from api.routes.chat import router as chat_router
from api.routes.documents import router as documents_router
from api.routes.agent import router as agent_router

load_dotenv()
logger = logging.getLogger(__name__)


# Pydantic Models

# Global state
db: DatabaseManager = None
conversation_memory = {}
rag_service = None
web_search_service = None
memory_service = None
langgraph_service = None
video_analyzer_service = None
scoratis_agent: ScoratisAgent = None

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
    global db, rag_service, web_search_service, memory_service, langgraph_service, video_analyzer_service, scoratis_agent

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
app.include_router(review_router)
app.include_router(transcripts_router)
app.include_router(health_router)
app.include_router(journals_router)
app.include_router(llm_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(agent_router)

# Run with: uvicorn main:app --reload --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
