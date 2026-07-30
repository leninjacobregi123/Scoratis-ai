"""
Health/stats/migration-status routes.

Uses database.get_database()'s singleton directly rather than main.py's
module-level `db` global - it's the same DatabaseManager instance (main.py's
lifespan already calls get_database() once at startup), without needing a
circular import back into main.
"""
from fastapi import APIRouter, Depends

from core.auth import get_current_user
from database import get_database
from models import User

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Unauthenticated health check for PaaS/uptime probes - global counts only, no per-user data."""
    db = get_database()
    stats = await db.get_user_stats()
    return {
        "status": "running",
        "message": "Scoratis FastAPI is healthy",
        "version": "3.0",
        "database": "PostgreSQL + pgvector",
        "features": ["RAG", "Web Search", "Embeddings"],
        "stats": stats
    }


@router.get("/stats")
async def get_stats(current_user: User = Depends(get_current_user)):
    """Get statistics for the authenticated user"""
    db = get_database()
    return await db.get_user_stats(user_id=current_user.id)


@router.get("/migrations/status")
async def get_migration_status():
    """Get database migration status (Alembic)"""
    db = get_database()
    return db.get_migration_status()
