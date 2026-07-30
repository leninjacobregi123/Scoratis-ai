from fastapi import APIRouter, HTTPException, StreamingResponse, Request
from fastapi.responses import FileResponse
from typing import Optional, List, Dict, Any
import json
import logging
import asyncio

from api.schemas import ChatMessage, TTSRequest
from llm_service import llm_service
from services.litellm_service import LLMGenerationError, separate_thinking_from_response
from prompts import (
    get_subject_prompt, CITATION_INSTRUCTIONS, RAG_CONTEXT_AWARENESS
)
from models import ProviderType
from conversation_analyzer import conversation_analyzer
from coqui_tts_service import coqui_tts_service
from services.citation_processor import get_citation_processor
from services.guardrail_service import GuardrailResult
from video_service import video_service
from config import settings
import backend.core.services as services

logger = logging.getLogger(__name__)
router = APIRouter()

_last_llm_error: Dict[str, Any] = {}
conversation_memory = {}

def generate_fallback(user_message: str, error_info: Dict[str, Any] = None) -> str:
    model_status = await llm_service.check_model_availability()
    if not model_status.get("available"):
        return {
            "error_type": model_status.get("error_type"),
            "suggestion": model_status.get("suggestion"),
            "message": model_status.get("message"),
            "model": llm_service.current_config.model if llm_service.current_config else None,
        }
    return {}

@router.get("/tutor-voices")
async def get_tutor_voices():
    if not request.text or len(request.text.strip()) < 2:
        raise HTTPException(status_code=400, detail="Text too short for TTS")

    audio_path = coqui_tts_service.synthesize(
        text=request.text,
        tutor_mode="socrates"
    )

    if audio_path and audio_path.exists():
        return FileResponse(
            path=str(audio_path),
            media_type="audio/mpeg",
            filename=f"response_{audio_path.stem}.mp3"
        )
    raise HTTPException(status_code=500, detail="TTS generation failed")

@router.post("/")
async def chat(message: ChatMessage):
    user_message = message.message.strip()
    session_id = message.session_id
    subject = message.subject or "general"

    if session_id not in conversation_memory:
        conversation_memory[session_id] = []
    
    conversation_id = await services.db.add_chat_message(session_id, 'user', user_message, subject=subject)
    conversation_memory[session_id].append({"role": "user", "content": user_message})

    async def generate():
        full_response = ""
        system_prompt = get_subject_prompt(subject)
        async for chunk in llm_service.generate_stream(messages=conversation_memory[session_id], system_prompt=system_prompt):
            full_response += chunk
            yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
        
        await services.db.add_chat_message(session_id, 'ai', full_response, subject=subject)
        conversation_memory[session_id].append({"role": "assistant", "content": full_response})
        yield f"data: {json.dumps({'done': True, 'full_response': full_response})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@router.post("/clear")
async def clear_chat(session_id: str = Query(...)):
