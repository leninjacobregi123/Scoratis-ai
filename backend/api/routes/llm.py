"""
LLM configuration and provider-management routes.

Uses database.get_database()'s singleton directly for db.get_session(),
same pattern as api/routes/health.py/journals.py - see health.py's
docstring for why.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update

from api.schemas import LLMConfigUpdate, LLMProviderCreate, LLMProviderUpdate, SessionModelUpdate
from config import settings
from core.auth import get_current_user
from database import get_database
from llm_service import llm_service
from models import User, ProviderType, PROVIDER_INFO, LLMProviderConfig
from services.encryption_service import get_encryption_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/providers")
async def get_llm_providers():
    """Get available LLM providers and their models"""
    availability = await llm_service.check_availability()
    models = llm_service.get_available_models()
    current = llm_service.get_current_config()

    return {
        "availability": availability,
        "models": models,
        "current": current,
    }


@router.post("/configure")
async def configure_llm(config: LLMConfigUpdate, current_user: User = Depends(get_current_user)):
    """
    Configure the LLM model with validation.

    By default, validates that the model is available before accepting.
    Set skip_validation=true to bypass validation (useful for downloading models).

    Raises HTTPException(400) on validation failure with:
    - error_type: model_not_installed, server_unavailable, insufficient_memory, timeout, authentication_error
    - message: Human-readable error message
    - suggestion: Actionable fix command

    NOTE: llm_service is currently a process-wide singleton, so this affects
    every user's requests until changed again - a known limitation to address
    when per-user LLM configuration isolation is built (not part of this pass).
    """
    provider = config.provider or settings.DEFAULT_LLM_PROVIDER
    db = get_database()

    # Fetch API key from database for cloud providers FIRST (needed for validation)
    api_key_encrypted = None
    try:
        provider_type = ProviderType(provider.lower())
        if PROVIDER_INFO.get(provider_type, {}).get("requires_api_key"):
            async with db.get_session() as session:
                stmt = select(LLMProviderConfig).where(
                    LLMProviderConfig.user_id == current_user.id,
                    LLMProviderConfig.provider == provider_type
                )
                result = await session.execute(stmt)
                provider_config = result.scalar_one_or_none()
                if provider_config:
                    api_key_encrypted = provider_config.api_key_encrypted
    except Exception as e:
        logger.warning(f"Could not fetch API key from database: {e}")

    # Validate model before accepting (unless explicitly skipped)
    if config.validate and not config.skip_validation:
        validation_result = await llm_service.validate_model_config(
            provider=provider,
            model=config.model,
            api_key_encrypted=api_key_encrypted,
            base_url=config.base_url,
            timeout_seconds=30,
        )

        if not validation_result.get("success"):
            # Raise HTTPException with structured error details
            raise HTTPException(
                status_code=400,
                detail={
                    "message": validation_result.get("message"),
                    "error_type": validation_result.get("error_type"),
                    "suggestion": validation_result.get("suggestion"),
                    "installed_models": validation_result.get("installed_models"),
                }
            )

    try:
        # API key already fetched above, just set the provider
        llm_service.set_provider(
            model=config.model,
            provider=provider,
            base_url=config.base_url,
            api_key_encrypted=api_key_encrypted,
            max_tokens=config.max_tokens or 2048,
            temperature=config.temperature or 0.7,
            context_length=config.context_length or 4096
        )

        # Reset video clients to pick up the new LLM configuration
        try:
            from video_service import reset_video_clients
            reset_video_clients()
        except Exception as e:
            logger.warning(f"Could not reset video clients: {e}")

        return {
            "success": True,
            "message": f"LLM configured to {provider}/{config.model}",
            "error_type": None,
            "config": llm_service.get_current_config()
        }
    except Exception as e:
        logger.error(f"Failed to configure LLM: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Failed to configure LLM: {str(e)}",
                "error_type": "configuration_error",
            }
        )


@router.get("/test")
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


@router.get("/health")
async def llm_health():
    """Comprehensive LLM health check"""
    return await llm_service.health_check()


@router.post("/validate")
async def validate_llm_model(config: LLMConfigUpdate):
    """
    Validate an LLM model configuration without applying it.

    Returns detailed error information if validation fails:
    - error_type: Type of error (model_not_installed, server_unavailable, etc.)
    - message: Human-readable error message
    - suggestion: Actionable fix (e.g., 'ollama pull llama3.2')
    """
    provider = config.provider or settings.DEFAULT_LLM_PROVIDER

    result = await llm_service.validate_model_config(
        provider=provider,
        model=config.model,
        base_url=config.base_url,
        timeout_seconds=30,
    )

    return result


@router.get("/model-status")
async def get_model_status():
    """
    Quick check if the current model is available and ready.

    Useful for showing status in the UI before attempting chat.
    """
    return await llm_service.check_model_availability()


@router.get("/providers/available")
async def get_available_llm_providers():
    """Get all available LLM providers with their models"""
    providers = llm_service.get_available_providers()
    return {
        "providers": providers,
        "total": len(providers)
    }


@router.get("/providers/configured")
async def get_configured_providers(current_user: User = Depends(get_current_user)):
    """Get all configured LLM provider configurations from database"""
    db = get_database()
    async with db.get_session() as session:
        stmt = select(LLMProviderConfig).where(LLMProviderConfig.user_id == current_user.id)
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


@router.post("/providers/configured", status_code=201)
async def create_provider_config(provider_config: LLMProviderCreate, current_user: User = Depends(get_current_user)):
    """Create a new LLM provider configuration with encrypted API key"""
    try:
        provider_type = ProviderType(provider_config.provider.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider_config.provider}")

    if provider_type == ProviderType.CUSTOM and not provider_config.base_url:
        raise HTTPException(status_code=400, detail="base_url is required for a Custom provider")

    encryption = get_encryption_service()
    db = get_database()

    try:
        async with db.get_session() as session:
            # If setting as default, unset other defaults
            if provider_config.is_default:
                await session.execute(
                    update(LLMProviderConfig)
                    .where(LLMProviderConfig.user_id == current_user.id)
                    .values(is_default=False)
                )

            # Encrypt API key if provided
            encrypted_key = None
            if provider_config.api_key:
                encrypted_key = encryption.encrypt(provider_config.api_key)

            new_config = LLMProviderConfig(
                user_id=current_user.id,
                provider=provider_type,
                name=provider_config.name,
                api_key_encrypted=encrypted_key,
                base_url=provider_config.base_url or PROVIDER_INFO.get(provider_type, {}).get("default_base_url"),
                extra_settings={"default_model": provider_config.default_model} if provider_config.default_model else None,
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
    except Exception:
        # Full exception (incl. the SQL statement/params on an IntegrityError)
        # goes to the server log only - it can include the API key value,
        # so it must never be echoed back in the client-facing detail.
        logger.exception(f"Failed to save provider config for user {current_user.id}, provider={provider_config.provider}")
        raise HTTPException(status_code=500, detail="Failed to save provider configuration. Please try again or contact support if this persists.")


@router.put("/providers/configured/{provider_id}")
async def update_provider_config(provider_id: int, update_data: LLMProviderUpdate, current_user: User = Depends(get_current_user)):
    """Update an existing LLM provider configuration"""
    encryption = get_encryption_service()
    db = get_database()

    async with db.get_session() as session:
        config = await session.get(LLMProviderConfig, provider_id)
        if not config or config.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Provider configuration not found")

        # If setting as default, unset other defaults
        if update_data.is_default:
            await session.execute(
                update(LLMProviderConfig)
                .where(LLMProviderConfig.user_id == current_user.id)
                .where(LLMProviderConfig.id != provider_id)
                .values(is_default=False)
            )

        if update_data.name is not None:
            config.name = update_data.name
        if update_data.api_key is not None:
            config.api_key_encrypted = encryption.encrypt(update_data.api_key)
        if update_data.base_url is not None:
            config.base_url = update_data.base_url
        if update_data.default_model is not None:
            config.extra_settings = {**(config.extra_settings or {}), "default_model": update_data.default_model}
        if update_data.is_active is not None:
            config.is_active = update_data.is_active
        if update_data.is_default is not None:
            config.is_default = update_data.is_default

        return {
            "message": "Provider configuration updated",
            "provider": config.to_dict()
        }


@router.delete("/providers/configured/{provider_id}")
async def delete_provider_config(provider_id: int, current_user: User = Depends(get_current_user)):
    """Delete an LLM provider configuration"""
    db = get_database()
    async with db.get_session() as session:
        config = await session.get(LLMProviderConfig, provider_id)
        if not config or config.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Provider configuration not found")

        await session.delete(config)
        return {"message": "Provider configuration deleted"}


@router.post("/providers/{provider_id}/test")
async def test_provider_config(provider_id: int, current_user: User = Depends(get_current_user)):
    """Test a configured provider by making a simple API call"""
    db = get_database()
    async with db.get_session() as session:
        config = await session.get(LLMProviderConfig, provider_id)
        if not config or config.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Provider configuration not found")

        provider_info = PROVIDER_INFO.get(config.provider, {})
        default_model = (
            (config.extra_settings or {}).get("default_model")
            or (provider_info.get("models", [""])[0] if provider_info.get("models") else "")
        )

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


@router.post("/session/model")
async def set_session_model(update_data: SessionModelUpdate, current_user: User = Depends(get_current_user)):
    """Set the LLM model for a specific chat session"""
    # conversation_memory is main.py's module-level global, shared with the
    # (not yet migrated) chat endpoints - imported lazily inside the
    # function body, not at module load time, to avoid a circular import
    # (main.py imports this router at its own top level).
    from main import conversation_memory

    db = get_database()

    # If provider_id is specified, get the configuration
    api_key_encrypted = None
    base_url = None
    provider = settings.DEFAULT_LLM_PROVIDER

    if update_data.provider_id:
        async with db.get_session() as session:
            config = await session.get(LLMProviderConfig, update_data.provider_id)
            if not config or config.user_id != current_user.id:
                raise HTTPException(status_code=404, detail="Provider configuration not found")

            api_key_encrypted = config.api_key_encrypted
            base_url = config.base_url
            provider = config.provider.value if isinstance(config.provider, ProviderType) else config.provider

    # Store the session model preference (in-memory for now)
    session_id = update_data.session_id
    if session_id not in conversation_memory:
        conversation_memory[session_id] = []

    # Update the global LLM service for this request
    llm_service.set_provider(
        model=update_data.model,
        provider=provider,
        base_url=base_url,
        api_key_encrypted=api_key_encrypted,
    )

    return {
        "message": f"Session {session_id} now using {provider}/{update_data.model}",
        "session_id": session_id,
        "provider": provider,
        "model": update_data.model
    }


@router.get("/available-models")
async def get_all_available_models():
    """Get all available models grouped by provider"""
    return {
        "models": llm_service.get_available_models(),
    }
