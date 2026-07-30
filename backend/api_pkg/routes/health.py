from fastapi import APIRouter
import backend.core.services as services

router = APIRouter()

@router.get("/health")
async def health_check():
    return await services.db.get_user_stats()

@router.get("/migrations/status")
async def get_migration_status():
