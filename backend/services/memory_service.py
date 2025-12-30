"""
Memory Service
Unified memory management combining short-term and long-term (RAG) memory
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession

from services.rag_service import get_rag_service, RAGResult
from config import settings

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """A chat message"""

    role: str  # 'user' or 'assistant'
    content: str


@dataclass
class MemoryContext:
    """Combined memory context for LLM"""

    short_term: List[Message]
    rag_journals: List[RAGResult]
    rag_conversations: List[RAGResult]
    formatted_context: str = ""


class MemoryService:
    """
    Unified memory service combining:
    - Short-term: Recent messages in current session
    - Long-term: RAG retrieval from journals and past conversations
    """

    def __init__(self):
        self.rag_service = get_rag_service()
        self.short_term_limit = settings.SHORT_TERM_MEMORY_LIMIT
        # In-memory storage for current session messages
        self._session_messages: Dict[str, List[Message]] = defaultdict(list)

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """
        Add a message to short-term memory.

        Args:
            session_id: Chat session ID
            role: 'user' or 'assistant'
            content: Message content
        """
        messages = self._session_messages[session_id]
        messages.append(Message(role=role, content=content))

        # Trim to limit
        if len(messages) > self.short_term_limit:
            self._session_messages[session_id] = messages[-self.short_term_limit :]

    def get_short_term_memory(self, session_id: str) -> List[Message]:
        """
        Get recent messages from short-term memory.

        Args:
            session_id: Chat session ID

        Returns:
            List of recent messages
        """
        return self._session_messages.get(session_id, [])

    def clear_session(self, session_id: str) -> None:
        """
        Clear short-term memory for a session.

        Args:
            session_id: Chat session ID
        """
        if session_id in self._session_messages:
            del self._session_messages[session_id]

    async def get_full_context(
        self,
        db: AsyncSession,
        session_id: str,
        current_query: str,
        user_id: int = 1,
    ) -> MemoryContext:
        """
        Get complete memory context (short-term + RAG).

        Args:
            db: Database session
            session_id: Current chat session ID
            current_query: User's current message
            user_id: User ID

        Returns:
            MemoryContext with all memory sources
        """
        # Get short-term memory
        short_term = self.get_short_term_memory(session_id)

        # Get RAG context
        rag_context = await self.rag_service.get_relevant_context(
            db, current_query, session_id, user_id
        )

        # Format for LLM
        formatted = self._format_full_context(
            short_term,
            rag_context.get("journals", []),
            rag_context.get("conversations", []),
        )

        return MemoryContext(
            short_term=short_term,
            rag_journals=rag_context.get("journals", []),
            rag_conversations=rag_context.get("conversations", []),
            formatted_context=formatted,
        )

    def _format_full_context(
        self,
        short_term: List[Message],
        journals: List[RAGResult],
        conversations: List[RAGResult],
    ) -> str:
        """
        Format all memory sources into LLM-ready context.

        Args:
            short_term: Recent messages
            journals: Relevant journal entries
            conversations: Relevant past conversations

        Returns:
            Formatted context string
        """
        parts = []

        # Add RAG context first (background knowledge)
        if journals:
            parts.append("**User's Relevant Journal Notes:**")
            for j in journals:
                parts.append(f"- [{j.title}]: {j.content[:300]}...")

        if conversations:
            parts.append("\n**Relevant Past Discussions:**")
            for c in conversations:
                sender = c.metadata.get("sender", "unknown")
                parts.append(f"- ({sender}): {c.content[:200]}...")

        # Add conversation history
        if short_term:
            parts.append("\n**Recent Conversation:**")
            for msg in short_term[-10:]:  # Last 10 messages for context
                role_label = "User" if msg.role == "user" else "Assistant"
                parts.append(f"{role_label}: {msg.content[:300]}...")

        return "\n".join(parts) if parts else ""

    def format_for_ollama(
        self, context: MemoryContext, current_message: str
    ) -> List[Dict[str, str]]:
        """
        Format memory context for Ollama chat API format.

        Args:
            context: MemoryContext object
            current_message: User's current message

        Returns:
            List of message dicts for Ollama
        """
        messages = []

        # Add system context with RAG information
        if context.formatted_context:
            system_content = (
                "You are Scoratis, a Socratic learning assistant. "
                "Use the following context to inform your responses:\n\n"
                f"{context.formatted_context}"
            )
            messages.append({"role": "system", "content": system_content})

        # Add short-term conversation history
        for msg in context.short_term:
            messages.append({"role": msg.role, "content": msg.content})

        # Add current message
        messages.append({"role": "user", "content": current_message})

        return messages


# Singleton instance
_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """Get or create the memory service singleton"""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service
