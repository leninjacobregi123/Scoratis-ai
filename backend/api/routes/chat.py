"""
Chat routes - the core Socratic tutoring conversation surface: plain and
streaming (SSE) chat, TTS, file-attachment chat, video-generation triggers,
and conversation history CRUD.

Service singletons (rag_service, web_search_service, memory_service,
langgraph_service, video_analyzer_service, scoratis_agent,
db) are resolved fresh via their own module's get_xxx()/get_database()
getter functions at the top of each route/handler that needs them, rather
than importing main.py's module-level globals directly - each service
module already holds its own canonical singleton state (initialized once
by main.py's lifespan, e.g. init_video_analyzer_service(...)), so calling
the getter here returns the exact same already-initialized instance with
no circular-import risk. conversation_memory has no such getter (it's a
plain dict, not a service with its own module) - imported lazily from main
inside each function body instead, since main.py imports this router at
its own top level (a module-level `from main import conversation_memory`
here would try to resolve before main.py has defined it).
"""
import logging
import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any

import aiofiles
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, Depends
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select

from api.schemas import ChatMessage, DeleteConversation, ConversationUpdate
from config import settings
from conversation_analyzer import conversation_analyzer, VideoTrigger
from core.auth import get_current_user
from coqui_tts_service import coqui_tts_service, TUTOR_VOICES
from database import get_database
from llm_service import llm_service
from models import ProviderType, PROVIDER_INFO, LLMProviderConfig, Document, SourceType, DocumentStatus, User
from prompts import detect_video_potential, get_system_prompt, CITATION_INSTRUCTIONS, RAG_CONTEXT_AWARENESS
from services import get_rag_service, get_web_search_service, get_memory_service, review_service
from services.agent import get_agent
from services.citation_processor import get_citation_processor
from services.encryption_service import get_encryption_service
from services.langgraph_service import get_langgraph_service
from services.litellm_service import LLMGenerationError, LLMError
from services.video_analyzer_service import get_video_analyzer_service
from services.video_job_service import start_video_job
from video_service import video_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


async def _seed_review_items(session_id: str, user_id: int) -> None:
    """Seed spaced-repetition review items from this turn's
    ConversationAnalyzer state. Called unconditionally after every AI turn
    (independent of whether LangGraph or the plain ConversationAnalyzer path
    handled video-trigger analysis) since `analyze_message` is a cheap local
    heuristic, not an LLM call - safe to run alongside either path.
    Best-effort: a seeding failure must never break the chat response the
    user is waiting on.
    """
    try:
        db = get_database()
        turn_state = conversation_analyzer.get_or_create_state(session_id).to_dict()
        async with db.get_session() as session:
            await review_service.seed_from_key_discoveries(
                session, user_id=user_id, discoveries=turn_state.get("key_discoveries", [])
            )
    except Exception as e:
        logger.warning(f"Review-item seeding failed (continuing): {e}")


import re

_INTERNAL_REASONING_TAG_RE = re.compile(
    r"\*{0,2}<pedagogical_plan>\*{0,2}[\s\S]*?</pedagogical_plan>\*{0,2}|<think>[\s\S]*?</think>",
    re.IGNORECASE,
)


def strip_internal_reasoning(text: str) -> str:
    """Strip <pedagogical_plan>/<think> scratchpad leaks the model
    occasionally emits despite MISSION.md instructing it not to (a model
    steerability gap, not something a prompt tweak reliably fixes).
    frontend/src/pages/Chat.jsx does the same stripping for the live
    stream, but that's client-side only - this covers the DB-persisted
    copy, which export/share read directly and unstripped otherwise."""
    if not text:
        return text
    return _INTERNAL_REASONING_TAG_RE.sub("", text).strip()


# ==================== CHAT ENDPOINTS ====================

# Store last LLM error for better user feedback
_last_llm_error: Dict[str, Any] = {}


def generate_fallback(user_message: str, error_info: Dict[str, Any] = None) -> str:
    """
    Generate contextual fallback response when LLM is unavailable.

    Provides specific feedback based on the error type:
    - model_not_installed: Tell user to download the model
    - server_unavailable: Tell user to start Ollama
    - insufficient_memory: Suggest smaller model
    - timeout: Model may be downloading
    """
    global _last_llm_error
    if error_info:
        _last_llm_error = error_info

    # Check if we have a specific LLM error to report
    if error_info:
        error_type = error_info.get("error_type", "")
        suggestion = error_info.get("suggestion", "")

        if error_type == "model_not_installed":
            model = error_info.get("model", "the selected model")
            return f"I'm unable to respond because the AI model '{model}' is not installed. To fix this, open your terminal and run: {suggestion}"

        elif error_type == "server_unavailable":
            return f"I'm unable to respond because the AI server is not running. To fix this: {suggestion}"

        elif error_type == "insufficient_memory":
            return f"I'm unable to respond because the selected AI model requires more memory than your system has available. {suggestion}"

        elif error_type == "timeout":
            return f"The AI model is taking too long to respond. {suggestion}"

        elif error_type == "authentication_error":
            return f"I'm unable to connect to the AI service due to an authentication issue. {suggestion}"

        elif error_type == "connection_error":
            return f"I'm unable to connect to the AI service. {suggestion}"

        elif error_type == "no_provider_configured":
            return "You haven't configured an AI provider yet. Add an API key for a provider (like Groq, OpenAI, or Anthropic) in Settings to start chatting."

    # Generic fallback responses based on user message
    msg_lower = user_message.lower().strip()

    if any(word in msg_lower for word in ["everything", "nothing", "all of it"]):
        return "Feeling overwhelmed? Let's start with something tiny and concrete. What's one specific thing you'd like to understand better? We'll take it step by step!"

    if any(phrase in msg_lower for phrase in ["don't know", "dont know", "idk", "confused"]):
        return "That's completely normal when learning something new! Confusion is actually the first step to understanding. Can you tell me what part feels most unclear? We'll tackle it together."

    if any(phrase in msg_lower for phrase in ["teach me", "learn", "start"]):
        return "I'd love to help you learn! To give you the best guidance, could you tell me: What topic are you interested in? And what do you already know about it (even if it's just a little)?"

    if any(phrase in msg_lower for phrase in ["help", "homework", "assignment"]):
        return "I'm here to help! Let's work through this together. What's the specific problem or question you're working on? Share it with me and we'll break it down step by step."

    return f"I apologize, but I'm having trouble connecting to the AI model. Please check your model settings or try again in a moment."


async def get_llm_error_info() -> Dict[str, Any]:
    """Get detailed error info about current LLM configuration."""
    model_status = await llm_service.check_model_availability()
    if not model_status.get("available"):
        return {
            "error_type": model_status.get("error_type"),
            "suggestion": model_status.get("suggestion"),
            "message": model_status.get("message"),
            "model": llm_service.current_config.model if llm_service.current_config else None,
        }
    return {}


async def _resolve_user_llm_config(db, user_id: int, requested_provider: Optional[str], requested_model: Optional[str]):
    """Resolve which provider/model/key this request should use, from the
    user's OWN configured LLMProviderConfig rows only - there is no
    deployment-wide default to fall back to (every account must configure
    its own key). Prefers the requested provider if given and usable,
    otherwise falls back to the user's own default/most-recent active
    config. Returns (provider, model, api_key_encrypted) with provider=None
    if the user has nothing usable configured.
    """
    async with db.get_session() as db_session:
        stmt = select(LLMProviderConfig).where(
            LLMProviderConfig.user_id == user_id,
            LLMProviderConfig.is_active == True
        )

        if requested_provider:
            try:
                provider_filter = ProviderType(requested_provider)
                stmt = stmt.where(LLMProviderConfig.provider == provider_filter)
            except ValueError:
                logger.warning(f"[MODEL SWITCH] Invalid provider: {requested_provider}")

        stmt = stmt.order_by(LLMProviderConfig.is_default.desc(), LLMProviderConfig.updated_at.desc())

        result = await db_session.execute(stmt)
        # first(), not scalar_one_or_none() - a user can have more than one
        # active config for the same provider (e.g. re-added after editing),
        # which isn't an error case worth crashing the request on.
        provider_config = result.scalars().first()

        # Requested provider had no usable config - fall back to the user's
        # own default/most-recent active config for ANY provider, rather
        # than failing outright just because their last-selected provider
        # lost its key.
        if not provider_config and requested_provider:
            fallback_stmt = (
                select(LLMProviderConfig)
                .where(LLMProviderConfig.user_id == user_id, LLMProviderConfig.is_active == True)
                .order_by(LLMProviderConfig.is_default.desc(), LLMProviderConfig.updated_at.desc())
            )
            result = await db_session.execute(fallback_stmt)
            provider_config = result.scalars().first()

        if not provider_config:
            return None, None, None

        provider = (
            provider_config.provider
            if isinstance(provider_config.provider, ProviderType)
            else ProviderType(provider_config.provider)
        )
        encrypted_key = provider_config.api_key_encrypted

        if not llm_service.litellm.has_api_key(provider, encrypted_key):
            return None, None, None

        model = (
            requested_model
            or (provider_config.extra_settings or {}).get("default_model")
            or next(iter(PROVIDER_INFO.get(provider, {}).get("models", [])), None)
        )
        if not model:
            return None, None, None

        return provider, model, encrypted_key

# ==================== CHAT ENDPOINTS ====================

@router.get("/chat/tutor-voices")
async def get_tutor_voices():
    """Get available voices for each tutor mode"""
    return {
        "voices": coqui_tts_service.get_available_voices(),
        "default": "socrates"
    }

class TTSRequest(BaseModel):
    text: str

@router.post("/chat/tts")
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

@router.post("/chat")
async def chat(message: ChatMessage, current_user: User = Depends(get_current_user)):
    """Chat with Scoratis AI assistant using RAG + Web Search augmentation"""
    db = get_database()
    from main import conversation_memory
    langgraph_service = get_langgraph_service()
    memory_service = get_memory_service()
    rag_service = get_rag_service()
    web_search_service = get_web_search_service()
    user_message = message.message.strip()
    session_id = message.session_id

    if not user_message:
        raise HTTPException(status_code=400, detail="No message provided")

    base_system_prompt = get_system_prompt()

    try:
        # Get or initialize conversation history
        if session_id not in conversation_memory:
            conversation_memory[session_id] = []

        # Save user message to database with embedding
        conversation_id = await db.add_chat_message(session_id, 'user', user_message, user_id=current_user.id)

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
        error_info = None
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

        except LLMGenerationError as llm_error:
            # Centralized error handling - extract structured error from LLMGenerationError
            logger.error(f"LLM Generation Error: {llm_error.error.message}")

            error_info = {
                "error_type": llm_error.error.error_type,
                "model": llm_error.error.model,
                "provider": llm_error.error.provider,
                "suggestion": llm_error.error.suggestion,
                "message": llm_error.error.message,
            }
            response_text = generate_fallback(user_message, error_info)
            source = "fallback"

        except Exception as e:
            # Fallback for any other unexpected errors
            logger.error(f"Unexpected LLM Error: {e}")

            # Try to get detailed info from model availability check
            error_info = await get_llm_error_info()
            if not error_info:
                error_info = {
                    "error_type": "unknown_error",
                    "message": str(e)[:200],
                    "suggestion": "Check logs for details or try again",
                }

            response_text = generate_fallback(user_message, error_info)
            source = "fallback"

        # Save AI response to database with embedding
        await db.add_chat_message(session_id, 'ai', strip_internal_reasoning(response_text), user_id=current_user.id)

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

        analyzer_ran_this_turn = False
        try:
            if langgraph_service:
                # Use LangGraph for intelligent video analysis (analysis only, no LLM call)
                lg_result = await langgraph_service.analyze_for_video(
                    session_id=session_id,
                    user_message=user_message,
                    ai_response=response_text,
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
                analyzer_ran_this_turn = True
                video_available = video_analysis.get('should_offer_video', False)
                video_topic = video_analysis.get('suggested_video_topic')
                learning_state_str = video_analysis.get('learning_state', 'initial')
                turn_count = video_analysis.get('turn_count', 0)
        except Exception as video_err:
            logger.warning(f"Video analysis error (continuing without): {video_err}")

        if not analyzer_ran_this_turn:
            # LangGraph handled video-trigger analysis above; ConversationAnalyzer's
            # own state still needs updating so review-item seeding has fresh data.
            conversation_analyzer.analyze_message(
                session_id=session_id, user_message=user_message, ai_response=response_text
            )
        await _seed_review_items(session_id, current_user.id)

        return {
            "reply": response_text,
            "source": source,
            "search_used": search_used,
            "session_id": session_id,
            "conversation_id": conversation_id,
            "model": current_config.get("model") if current_config else None,
            # New video fields for user-triggered generation
            "video_available": video_available,
            "video_topic": video_topic,
            "video_concepts": video_concepts,
            "video_type": video_type,
            "learning_state": learning_state_str,
            "turn_count": turn_count,
            # Error info for frontend (only present if source is "fallback")
            "error_info": error_info if source == "fallback" else None,
        }

    except Exception as e:
        logger.error(f"Chat Error: {e}")

        # Try to get specific error info
        error_info = await get_llm_error_info()
        response_text = generate_fallback(user_message, error_info)

        try:
            await db.add_chat_message(session_id, 'ai', strip_internal_reasoning(response_text), user_id=current_user.id)
        except:
            pass
        return {
            "reply": response_text,
            "source": "fallback",
            "session_id": session_id,
            "error": str(e),
            "error_info": error_info,
            "search_used": False,
            "video_available": False,
            "video_topic": None,
            "video_concepts": [],
            "video_type": None,
            "learning_state": "initial",
            "turn_count": 0
        }

@router.post("/chat/stream")
async def chat_stream(message: ChatMessage, current_user: User = Depends(get_current_user)):
    """Stream chat responses from Scoratis AI with RAG + Web Search"""
    db = get_database()
    from main import conversation_memory
    langgraph_service = get_langgraph_service()
    memory_service = get_memory_service()
    rag_service = get_rag_service()
    scoratis_agent = get_agent()
    video_analyzer_service = get_video_analyzer_service()
    web_search_service = get_web_search_service()
    user_message = message.message.strip()
    session_id = message.session_id

    if not user_message:
        raise HTTPException(status_code=400, detail="No message provided")

    # === Resolve provider/model/key for this request, shared by both the
    # agentic and non-agentic paths below, from the user's OWN configured
    # providers only - there is no deployment-wide default to fall back to
    # (every account, new or existing, must configure its own key). The
    # agent has no per-request provider param, so this also gets applied to
    # the shared llm_service singleton via set_provider() right before
    # invoking it. ===
    resolved_provider, resolved_model, resolved_api_key_encrypted = await _resolve_user_llm_config(
        db, current_user.id, message.provider, message.model
    )

    if resolved_provider is None:
        async def no_provider_stream():
            fallback = generate_fallback(user_message, {"error_type": "no_provider_configured"})
            yield f"data: {json.dumps({'chunk': fallback, 'done': True})}\n\n"
        return StreamingResponse(
            no_provider_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    # Several helper calls within this request - RAG query reformulation,
    # the post-response video-worthiness check, and the agent's internal
    # tool-calling - all go through llm_service without
    # passing an explicit provider/model/key, so they fall back to
    # llm_service.current_config (a shared, process-wide singleton). Apply
    # the resolution above to it unconditionally so those calls use the
    # same provider/key as the main response instead of a stale prior
    # request's config.
    llm_service.set_provider(
        model=resolved_model,
        provider=resolved_provider.value,
        api_key_encrypted=resolved_api_key_encrypted
    )

    # === AGENTIC MODE: Use full agent when use_reasoning is enabled ===
    use_reasoning = message.use_reasoning if message.use_reasoning is not None else False

    if use_reasoning and scoratis_agent:
        logger.info(f"Using agentic mode for session {session_id}")

        async def generate_agent_stream_internal():
            full_response = ""
            try:
                async with db.get_session() as db_session:
                    async for event in scoratis_agent.stream(
                        session_id=session_id,
                        message=user_message,
                        db_session=db_session,
                        user_id=current_user.id
                    ):
                        event_type = event.get("type")

                        if event_type == "sources":
                            # Stream sources for citation preview
                            yield f"data: {json.dumps(event)}\n\n"

                        elif event_type == "tool_start":
                            # Show tool execution starting (chain of thought UI)
                            yield f"data: {json.dumps({'type': 'tool_start', 'tool': event['tool'], 'args': event.get('args', {})})}\n\n"

                        elif event_type == "tool_end":
                            # Show tool execution result
                            yield f"data: {json.dumps({'type': 'tool_end', 'tool': event['tool'], 'result': event.get('result', {})})}\n\n"

                        elif event_type == "thinking":
                            # Stream thinking/reasoning steps
                            yield f"data: {json.dumps({'type': 'thinking', 'content': event.get('content', '')})}\n\n"

                        elif event_type == "phase":
                            # Stream phase changes
                            yield f"data: {json.dumps({'type': 'phase', 'phase': event.get('phase', '')})}\n\n"

                        elif event_type == "token":
                            # Stream response text
                            full_response += event.get("content", "")
                            yield f"data: {json.dumps({'chunk': event['content'], 'done': False})}\n\n"

                        elif event_type == "done":
                            # Ensure response is never empty
                            final_response = full_response.strip() if full_response else ""
                            if not final_response:
                                final_response = event.get("response") or "I apologize, but I couldn't generate a complete response."

                            # Save to database
                            await db.add_chat_message(session_id, 'ai', strip_internal_reasoning(final_response), user_id=current_user.id)

                            # Final event with metadata
                            final_data = {
                                'chunk': '',
                                'done': True,
                                'full_response': final_response,
                                'session_id': session_id,
                                'model': event.get('metadata', {}).get('model'),
                                'sources': event.get('metadata', {}).get('sources', []),
                                'tools_used': event.get('metadata', {}).get('tools_used', 0),
                                'mode': 'agent',
                            }
                            yield f"data: {json.dumps(final_data)}\n\n"

            except Exception as e:
                logger.error(f"Agent stream error: {e}")
                error_data = {
                    'chunk': f"I apologize, but I encountered an error while reasoning: {str(e)}",
                    'done': True,
                    'error': str(e)
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            generate_agent_stream_internal(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    # Get the system prompt
    base_system_prompt = get_system_prompt()

    # Get or initialize conversation history
    if session_id not in conversation_memory:
        conversation_memory[session_id] = []

    # Save user message to database with embedding
    conversation_id = await db.add_chat_message(session_id, 'user', user_message, user_id=current_user.id)

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
    # Documents are always searched when the user has any - there's no
    # manual toggle for this in the UI anymore.
    rag_context_xml = ""
    rag_sources = []
    rag_chunk_mapping = {}
    use_web_search = message.use_web_search if message.use_web_search is not None else True

    # Get conversation history for query reformulation (last 10 messages)
    conversation_history_for_rag = conversation_memory.get(session_id, [])[-10:]

    try:
        async with db.get_session() as db_session:
            rag_result = await rag_service.get_context_with_citations(
                db_session,
                user_message,
                conversation_history=conversation_history_for_rag,
                use_query_reformulation=True,
                llm_service=llm_service,
            )
            rag_context_xml = rag_result.get("context_xml", "")
            rag_sources = rag_result.get("sources", [])
            rag_chunk_mapping = rag_result.get("chunk_mapping", {})

            # Log query reformulation if it occurred
            reformulation_info = rag_result.get("reformulation_info")
            if reformulation_info:
                logger.info(f"Query reformulated: '{reformulation_info.get('original_query')}' -> '{reformulation_info.get('reformulated_query')}'")
    except Exception as rag_error:
        logger.warning(f"Document RAG search error (continuing without): {rag_error}")

    # === Long-term memory: journal entries + past conversations ===
    # Independent of document RAG above - previously this only ran as a
    # fallback when document search *threw*, meaning journals/past chats were
    # never actually recalled in normal operation. Runs every turn now,
    # alongside document context rather than instead of it.
    memory_context_text = ""
    try:
        async with db.get_session() as db_session:
            relevant_context = await rag_service.get_relevant_context(
                db_session, user_message, session_id, user_id=current_user.id
            )
            memory_context_text = rag_service.format_context_for_llm(relevant_context)
    except Exception as memory_error:
        logger.warning(f"Journal/conversation memory search error (continuing without): {memory_error}")

    # === Web Search: Proactive search when enabled ===
    web_search_context = ""
    web_search_results = []
    search_trail_data = {"attempts": []}

    if use_web_search:
        try:
            web_search_service = get_web_search_service()
            if web_search_service.enabled:
                # Perform proactive web search
                logger.info(f"Web search enabled, searching for: {user_message[:50]}...")
                search_results = await web_search_service.search(user_message)

                if search_results:
                    web_search_results = search_results
                    web_search_context = web_search_service.format_results_for_llm(search_results)
                    logger.info(f"Web search found {len(search_results)} results")

                    # Build search trail for UI
                    search_trail_data["attempts"].append({
                        "source": "web_search",
                        "query": user_message[:100],
                        "results_count": len(search_results),
                        "results": [
                            {
                                "title": r.title,
                                "url": r.url,
                                "snippet": r.snippet[:150] + "..." if len(r.snippet) > 150 else r.snippet
                            }
                            for r in search_results[:3]
                        ]
                    })
                else:
                    search_trail_data["attempts"].append({
                        "source": "web_search",
                        "query": user_message[:100],
                        "results_count": 0,
                        "results": []
                    })
        except Exception as web_error:
            logger.warning(f"Web search error (continuing without): {web_error}")

    # Build enhanced system prompt with RAG context, web search, and citation instructions
    context_parts = []

    # Add RAG context if available
    if rag_context_xml:
        context_parts.append(f"DOCUMENT CONTEXT:\n{rag_context_xml}")

    # Add recalled journal entries / past conversations if available
    if memory_context_text:
        context_parts.append(memory_context_text)

    # Add web search context if available
    if web_search_context:
        context_parts.append(f"\n{web_search_context}")

    # Build system prompt with all context
    if rag_context_xml and rag_sources:
        combined_context = "\n\n".join(context_parts) if context_parts else ""
        system_prompt = f"""{base_system_prompt}

{RAG_CONTEXT_AWARENESS}

{CITATION_INSTRUCTIONS}

---
{combined_context}
---"""
    elif context_parts:
        # Has some context (RAG or web search)
        combined_context = "\n\n".join(context_parts)
        system_prompt = f"{base_system_prompt}\n\n---\nRELEVANT CONTEXT:\n{combined_context}\n---"
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

            # Stream search trail (shows what was searched - documents and/or web)
            if search_trail_data["attempts"] or rag_sources:
                search_trail_data["attempts"].insert(0, {
                    "source": "documents",
                    "query": user_message[:100],
                    "results_count": len(rag_sources) if rag_sources else 0,
                })

                search_trail_event = {
                    "type": "search_trail",
                    "search_trail": search_trail_data
                }
                yield f"data: {json.dumps(search_trail_event)}\n\n"

            # Stream the response using the provider/model/key resolved above
            # (shared with the agentic branch, so both paths behave identically)
            stream_kwargs = {
                "messages": conversation_memory[session_id],
                "system_prompt": system_prompt,
                "provider": resolved_provider,
                "model": resolved_model,
            }
            if resolved_api_key_encrypted:
                stream_kwargs["api_key_encrypted"] = resolved_api_key_encrypted
                logger.info(f"[MODEL SWITCH] Using model override only: {message.model}")

            logger.info(f"[MODEL SWITCH] Final stream_kwargs keys: {list(stream_kwargs.keys())}")

            async for chunk in llm_service.generate_stream(**stream_kwargs):
                full_response += chunk
                yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"

            # Save complete response to database with embedding
            await db.add_chat_message(session_id, 'ai', strip_internal_reasoning(full_response), user_id=current_user.id)

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

            analyzer_ran_this_turn = False
            try:
                # First, get turn count from LangGraph or conversation analyzer
                lg_result = None  # Initialize for later use
                if langgraph_service:
                    lg_result = await langgraph_service.analyze_for_video(
                        session_id=session_id,
                        user_message=user_message,
                        ai_response=full_response,
                    )
                    learning_state_str = lg_result.get("learning_state", "initial")
                    turn_count = lg_result.get("turn_count", 0)
                else:
                    video_analysis = conversation_analyzer.analyze_message(
                        session_id=session_id,
                        user_message=user_message,
                        ai_response=full_response
                    )
                    analyzer_ran_this_turn = True
                    learning_state_str = video_analysis.get('learning_state', 'initial')
                    turn_count = video_analysis.get('turn_count', 0)

                # === NEW: Automatic Video Generation Decision ===
                video_analyzer = get_video_analyzer_service()
                if video_analyzer:
                    decision = await video_analyzer.should_auto_generate(
                        session_id=session_id,
                        user_message=user_message,
                        ai_response=full_response,
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
                        task_id = await start_video_job(
                            user_id=current_user.id,
                            topic=decision.topic,
                            quality="high",
                            duration=decision.duration_seconds,
                            context=video_context,
                            session_id=session_id,
                            auto_generated=True,
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

            if not analyzer_ran_this_turn:
                conversation_analyzer.analyze_message(
                    session_id=session_id, user_message=user_message, ai_response=full_response
                )
            await _seed_review_items(session_id, current_user.id)

            # === Citation Processing: Convert [citation:chunk_id] to footnotes ===
            formatted_response = full_response
            footnotes_section = ""
            citation_info = None

            if rag_sources and rag_chunk_mapping:
                try:
                    citation_processor = get_citation_processor()
                    formatted_response, footnotes_section, used_sources = citation_processor.format_response_with_footnotes(
                        full_response, rag_sources, rag_chunk_mapping
                    )
                    citation_info = {
                        "citations_used": len(used_sources),
                        "total_sources": len(rag_sources),
                    }
                except Exception as citation_err:
                    logger.warning(f"Citation processing error: {citation_err}")

            final_data = {
                'chunk': '',
                'done': True,
                'full_response': full_response,  # Original with [citation:chunk_id] tags
                'formatted_response': formatted_response,  # With superscript¹ numbers
                'footnotes': footnotes_section,  # Sources section
                'citation_info': citation_info,  # Metadata about citations
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
                'auto_video': auto_video_info,  # None if not auto-generating
            }
            yield f"data: {json.dumps(final_data)}\n\n"

        except LLMGenerationError as llm_error:
            # Centralized error handling - extract structured error
            logger.error(f"Stream LLM Error: {llm_error.error.message}")

            error_info = {
                "error_type": llm_error.error.error_type,
                "model": llm_error.error.model,
                "provider": llm_error.error.provider,
                "suggestion": llm_error.error.suggestion,
                "message": llm_error.error.message,
            }
            fallback = generate_fallback(user_message, error_info)
            error_data = {
                'chunk': fallback,
                'done': True,
                'error': llm_error.error.message,
                'error_info': error_info,
                'full_response': fallback,
                'search_used': False,
                'video_available': False,
                'video_topic': None,
                'video_concepts': [],
                'video_type': None,
                'learning_state': 'initial',
                'turn_count': 0,
                'auto_video': None
            }
            yield f"data: {json.dumps(error_data)}\n\n"
            try:
                await db.add_chat_message(session_id, 'ai', fallback, user_id=current_user.id)
                conversation_memory[session_id].append({
                    "role": "assistant",
                    "content": fallback
                })
            except:
                pass

        except Exception as e:
            # Fallback for unexpected errors
            logger.error(f"Stream Error: {e}")

            # Try to get structured error info
            error_info = await get_llm_error_info()
            fallback = generate_fallback(user_message, error_info)
            error_data = {
                'chunk': fallback,
                'done': True,
                'error': str(e),
                'error_info': error_info,
                'full_response': fallback,
                'search_used': False,
                'video_available': False,
                'video_topic': None,
                'video_concepts': [],
                'video_type': None,
                'learning_state': 'initial',
                'turn_count': 0,
                'auto_video': None
            }
            yield f"data: {json.dumps(error_data)}\n\n"
            try:
                await db.add_chat_message(session_id, 'ai', fallback, user_id=current_user.id)
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

@router.post("/chat/clear")
async def clear_chat(session_id: str = "default", current_user: User = Depends(get_current_user)):
    """Clear conversation memory"""
    db = get_database()
    from main import conversation_memory
    memory_service = get_memory_service()
    if session_id in conversation_memory:
        del conversation_memory[session_id]
    # Clear memory service
    memory_service.clear_session(session_id)
    # Reset conversation analyzer state
    conversation_analyzer.reset_session(session_id)
    # Clear from database
    await db.clear_conversation(session_id, user_id=current_user.id)
    return {"message": "Conversation cleared", "session_id": session_id}


@router.get("/chat/session/{session_id}/state")
async def get_session_state(session_id: str):
    """Get the learning state for a session"""
    state = conversation_analyzer.get_or_create_state(session_id)
    return state.to_dict()


@router.post("/chat/with-attachment")
async def chat_with_attachment(
    message: str = Form(...),
    session_id: str = Form("default"),
    file: Optional[UploadFile] = File(None),
    use_web_search: bool = Form(True),
    use_reasoning: bool = Form(False),
    provider: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
):
    """
    Chat with an optional file attachment.

    The file will be uploaded and processed for RAG, then included
    in the context for the chat response.

    This is a combined endpoint that:
    1. Uploads the file (if provided)
    2. Processes it inline (for small files) or queues it
    3. Returns a chat response with the document context

    Returns:
        Streaming response with document upload status and chat response
    """
    db = get_database()
    user_message = message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message is required")

    document_id = None
    document_title = None

    # Handle file upload if provided
    if file and file.filename:
        file_ext = Path(file.filename).suffix.lower().lstrip(".")

        # Validate file type
        if file_ext not in settings.ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Allowed: {settings.ALLOWED_FILE_TYPES}"
            )

        # Validate file size
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)

        max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB"
            )

        # Save file
        unique_id = str(uuid.uuid4())[:8]
        safe_filename = f"{unique_id}_{file.filename}"
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / safe_filename

        try:
            async with aiofiles.open(file_path, "wb") as f:
                content = await file.read()
                await f.write(content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

        # Create document record
        document_title = Path(file.filename).stem
        async with db.get_session() as session:
            document = Document(
                user_id=current_user.id,
                title=document_title,
                content="",
                source_type=SourceType.UPLOAD,
                file_path=str(file_path),
                file_type=file_ext,
                file_size=file_size,
                document_metadata={"original_filename": file.filename, "attached_to_chat": True},
                status=DocumentStatus.PENDING,
            )
            session.add(document)
            await session.flush()
            document_id = document.id

        # Queue for background processing
        try:
            from tasks.ingestion_tasks import process_document_task
            task = process_document_task.delay(document_id)
            logger.info(f"Document {document_id} queued for processing: {task.id}")
        except Exception as task_error:
            logger.warning(f"Failed to queue document processing: {task_error}")

    # Create chat message with options
    chat_message = ChatMessage(
        message=user_message,
        session_id=session_id,
        attachment_ids=[document_id] if document_id else None,
        use_web_search=use_web_search,
        use_reasoning=use_reasoning,
        provider=provider,
        model=model,
    )

    # Stream response using existing chat_stream logic
    async def combined_stream():
        # First, emit document upload info if a file was attached
        if document_id:
            upload_event = {
                "type": "upload",
                "document_id": document_id,
                "document_title": document_title,
                "status": "processing",
            }
            yield f"data: {json.dumps(upload_event)}\n\n"

        # Now stream the actual chat response
        # Re-use the streaming logic from chat_stream
        response = await chat_stream(chat_message, current_user)

        # Forward the streaming response
        async for chunk in response.body_iterator:
            yield chunk

    return StreamingResponse(
        combined_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/chat/session/{session_id}/summary")
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


@router.post("/chat/generate-video")
async def generate_video_from_chat(request: GenerateVideoFromChatRequest, current_user: User = Depends(get_current_user)):
    """
    User-triggered video generation using LangGraph conversation context.
    Generates a 15-30 second focused educational video.

    This endpoint is called when user clicks the "Generate Video" button
    that appears after video_available=true in chat response.
    """
    langgraph_service = get_langgraph_service()
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
        task_id = await start_video_job(
            user_id=current_user.id,
            topic=topic,
            quality="high",
            duration=20,  # Short focused video
            context=generation_context,
            session_id=session_id,
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


@router.post("/chat/video/trigger")
async def trigger_video_generation(request: VideoTriggerRequest, current_user: User = Depends(get_current_user)):
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
        task_id = await start_video_job(
            user_id=current_user.id,
            topic=video_topic,
            quality="high",
            context=video_context,  # Pass context for LLM-based generation
            session_id=request.session_id,
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


@router.post("/chat/video/context-aware")
async def context_aware_video_generation(request: ContextAwareVideoRequest, current_user: User = Depends(get_current_user)):
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
        task_id = await start_video_job(
            user_id=current_user.id,
            topic=topic,
            quality="high",
            context=video_context if request.use_context else None,
            session_id=request.session_id,
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


@router.get("/chat/video/context/{session_id}")
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

@router.get("/chat/history")
async def get_conversation_history(limit: int = Query(20, le=50), current_user: User = Depends(get_current_user)):
    """Get conversation history"""
    db = get_database()
    conversations = await db.get_conversations(user_id=current_user.id, limit=limit)
    return {"conversations": conversations}

@router.get("/chat/conversations")
async def get_all_conversations(limit: int = Query(50, le=100), current_user: User = Depends(get_current_user)):
    """Get all conversations for sidebar"""
    db = get_database()
    conversations = await db.get_conversations(user_id=current_user.id, limit=limit)
    return {"conversations": conversations}

@router.get("/chat/conversation/{conversation_id}")
async def get_conversation_messages(conversation_id: str, current_user: User = Depends(get_current_user)):
    """Get messages for a conversation"""
    db = get_database()
    # Handle both integer IDs and session IDs
    try:
        conv_id = int(conversation_id)
        messages = await db.get_conversation_messages_by_id(conv_id, user_id=current_user.id)
        # The real session_id, distinct from this numeric conversation_id - the
        # frontend needs it for share/export calls, which key off session_id.
        session_id = await db.get_conversation_session_id(conv_id, user_id=current_user.id)
    except ValueError:
        messages = await db.get_conversation_messages(conversation_id, user_id=current_user.id)
        session_id = conversation_id
    return {
        "messages": messages,
        "conversation_id": conversation_id,
        "session_id": session_id,
    }

@router.put("/chat/conversation/{conversation_id}")
async def update_conversation(conversation_id: int, data: ConversationUpdate, current_user: User = Depends(get_current_user)):
    """Update conversation (rename)"""
    db = get_database()
    if data.title:
        await db.update_conversation_title(conversation_id, data.title, user_id=current_user.id)
    return {"message": "Conversation updated"}

@router.delete("/chat/conversation/{conversation_id}")
async def delete_conversation(conversation_id: int, data: DeleteConversation = None, current_user: User = Depends(get_current_user)):
    """Delete a conversation"""
    db = get_database()
    permanent = data.permanent if data else False
    await db.delete_conversation(conversation_id, user_id=current_user.id, permanent=permanent)
    return {"message": "Conversation deleted" if permanent else "Moved to trash"}

# RAG Search endpoint for debugging/testing
@router.get("/rag/search")
async def rag_search(q: str = Query(..., min_length=1)):
    """Test RAG semantic search"""
    db = get_database()
    rag_service = get_rag_service()
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


