"""
Transcript export (Markdown download) and sharing (unauthenticated
read-only link). See services/export_service.py.

Routes aren't prefixed with /transcripts because they extend the existing
/chat/session/{session_id} URL space the frontend already uses, plus one
public /shared/{token} endpoint that intentionally has no auth dependency.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user, get_db
from models import ChatMessage, Conversation, User
from services.export_service import build_markdown_transcript, generate_share_token

logger = logging.getLogger(__name__)
router = APIRouter(tags=["transcripts"])


async def _get_owned_conversation(session: AsyncSession, session_id: str, user_id: int) -> Conversation:
    result = await session.execute(
        select(Conversation).where(
            Conversation.session_id == session_id, Conversation.user_id == user_id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


async def _get_messages(session: AsyncSession, conversation_id: int):
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.timestamp.asc())
    )
    return list(result.scalars().all())


@router.get("/chat/session/{session_id}/export")
async def export_transcript(
    session_id: str,
    format: str = Query("md", pattern="^(md)$"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    conversation = await _get_owned_conversation(session, session_id, current_user.id)
    messages = await _get_messages(session, conversation.id)

    markdown = build_markdown_transcript(conversation, messages)
    filename = f"{(conversation.title or 'transcript')[:50].replace(' ', '_')}.md"

    return PlainTextResponse(
        content=markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/chat/session/{session_id}/share")
async def share_conversation(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    conversation = await _get_owned_conversation(session, session_id, current_user.id)

    if not conversation.share_token:
        conversation.share_token = generate_share_token()
        await session.flush()

    return {"share_token": conversation.share_token}


@router.delete("/chat/session/{session_id}/share")
async def unshare_conversation(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    conversation = await _get_owned_conversation(session, session_id, current_user.id)
    conversation.share_token = None
    await session.flush()
    return {"share_token": None}


@router.get("/shared/{token}")
async def get_shared_transcript(
    token: str,
    session: AsyncSession = Depends(get_db),
):
    """Public, unauthenticated read-only view of a shared conversation."""
    result = await session.execute(select(Conversation).where(Conversation.share_token == token))
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Shared conversation not found")

    messages = await _get_messages(session, conversation.id)

    return {
        "title": conversation.title,
        "subject": conversation.subject,
        "messages": [
            {"role": m.sender, "content": m.message, "timestamp": m.timestamp.isoformat() if m.timestamp else None}
            for m in messages
        ],
    }
