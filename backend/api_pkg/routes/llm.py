from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
import logging
from api.schemas import (
    LLMConfigUpdate, LLMProviderCreate, LLMProviderUpdate, 
    SessionModelUpdate
)
from llm_service import llm_service, RECOMMENDED_MODELS
from models import ProviderType, PROVIDER_INFO, LLMProviderConfig
from services.encryption_service import get_encryption_service
import backend.core.services as services

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/providers")
async def get_llm_providers():
    provider = config.provider or "ollama"
    api_key_encrypted = None
    
    try:
        provider_type = ProviderType(provider.lower())
        if PROVIDER_INFO.get(provider_type, {}).get("requires_api_key"):
            async with services.db.get_session() as session:
                from sqlalchemy import select
                stmt = select(LLMProviderConfig).where(
                    LLMProviderConfig.user_id == 1,
                    LLMProviderConfig.provider == provider_type
                )
                result = await session.execute(stmt)
                provider_config = result.scalar_one_or_none()
                if provider_config:
                    api_key_encrypted = provider_config.api_key_encrypted
    except Exception as e:
        logger.warning(f"Could not fetch API key from database: {e}")

    if config.validate and not config.skip_validation:
        validation_result = await llm_service.validate_model_config(
            provider=provider,
            model=config.model,
            api_key_encrypted=api_key_encrypted,
            base_url=config.base_url,
            timeout_seconds=30,
        )

        if not validation_result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=validation_result
            )

    try:
        llm_service.set_provider(
            model=config.model,
            provider=provider,
            base_url=config.base_url,
            api_key_encrypted=api_key_encrypted,
            max_tokens=config.max_tokens or 2048,
            temperature=config.temperature or 0.7,
            context_length=config.context_length or 4096
        )
        return {
            "success": True,
            "message": f"LLM configured to {provider}/{config.model}",
            "config": llm_service.get_current_config()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test")
async def test_llm():
    return await llm_service.health_check()

@router.get("/providers/configured")
async def get_configured_providers():
    try:
        provider_type = ProviderType(provider_config.provider.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider_config.provider}")

    encryption = get_encryption_service()
    async with services.db.get_session() as session:
        if provider_config.is_default:
            from sqlalchemy import update
            await session.execute(
                update(LLMProviderConfig)
                .where(LLMProviderConfig.user_id == 1)
                .values(is_default=False)
            )

        encrypted_key = encryption.encrypt(provider_config.api_key) if provider_config.api_key else None
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
        return {"id": new_config.id, "message": "Provider configured successfully"}

@router.get("/available-models")
async def get_all_available_models():
