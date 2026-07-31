"""
Agentic chat routes (/agent/*) - the multi-step-reasoning agent, as
opposed to the plain/streaming chat in api/routes/chat.py.
"""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.routes.chat import chat_stream
from api.schemas import ChatMessage
from core.auth import get_current_user
from database import get_database
from models import User
from services import get_rag_service, get_web_search_service
from services.agent import get_agent
from services.langgraph_service import get_langgraph_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])


class AgenticChatMessage(BaseModel):
    """Request model for agentic chat"""
    message: str
    session_id: str = "default"


@router.post("/chat")
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
    scoratis_agent = get_agent()
    db = get_database()

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


@router.post("/chat/stream")
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
    scoratis_agent = get_agent()
    db = get_database()

    if not message.message.strip():
        raise HTTPException(status_code=400, detail="No message provided")

    if not scoratis_agent:
        # Fallback to standard streaming
        return await chat_stream(ChatMessage(
            message=message.message,
            session_id=message.session_id,
        ), current_user)

    async def generate_agent_stream():
        full_response = ""
        try:
            async with db.get_session() as db_session:
                async for event in scoratis_agent.stream(
                    session_id=message.session_id,
                    message=message.message.strip(),
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


@router.get("/tools")
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


@router.get("/status")
async def get_agent_status():
    """
    Get the status of the Scoratis Agent.

    Returns information about whether the agent is initialized
    and what capabilities are available.
    """
    agent = get_agent()
    rag_service = get_rag_service()
    web_search_service = get_web_search_service()
    langgraph_service = get_langgraph_service()

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
