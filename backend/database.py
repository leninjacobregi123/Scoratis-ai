"""
PostgreSQL Database Manager with SQLAlchemy ORM
Supports pgvector for RAG embeddings and Alembic migrations
"""

import logging
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from contextlib import asynccontextmanager
import json

from sqlalchemy import create_engine, select, func, and_, or_, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from config import settings
from models import Base, User, Folder, Journal, Conversation, ChatMessage, LearningState
from services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

# Migration mode: 'alembic' for version-controlled migrations, 'auto' for create_all
MIGRATION_MODE = os.getenv("MIGRATION_MODE", "auto")


class DatabaseManager:
    """PostgreSQL Database Manager with SQLAlchemy ORM"""

    def __init__(self):
        # Sync engine (for migrations and init)
        self.sync_engine = create_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
        )
        self.SyncSession = sessionmaker(bind=self.sync_engine)

        # Async engine (for API operations)
        self.async_engine = create_async_engine(
            settings.DATABASE_URL_ASYNC,
            echo=False,
            pool_pre_ping=True,
        )
        self.AsyncSession = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        self.embedding_service = None  # Lazy load

    def _get_embedding_service(self):
        """Lazy load embedding service"""
        if self.embedding_service is None:
            try:
                self.embedding_service = get_embedding_service()
            except Exception as e:
                logger.warning(f"Failed to load embedding service: {e}")
                return None
        return self.embedding_service

    def init_database(self, use_alembic: bool = None):
        """
        Initialize database schema.

        Args:
            use_alembic: If True, use Alembic migrations. If False, use create_all.
                        If None, use MIGRATION_MODE environment variable.
        """
        if use_alembic is None:
            use_alembic = MIGRATION_MODE == "alembic"

        if use_alembic:
            self._run_alembic_migrations()
        else:
            # Legacy mode: direct table creation
            logger.info("Using SQLAlchemy create_all for database initialization")
            Base.metadata.create_all(self.sync_engine)

        # NOTE: no longer auto-seeding a default user here now that real
        # signup/login exists (see /auth/signup) - a hardcoded id=1 row
        # bypasses the users_id_seq sequence and collides with the first
        # real signup. See migration 002 for the one-time sequence repair
        # on databases that already have this legacy row.

    def _run_alembic_migrations(self):
        """Run Alembic migrations to upgrade database schema."""
        try:
            from alembic.config import Config
            from alembic import command
            import os

            logger.info("Running Alembic migrations...")

            # Get the directory containing this file
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            alembic_ini = os.path.join(backend_dir, "alembic.ini")

            if not os.path.exists(alembic_ini):
                logger.warning("alembic.ini not found, falling back to create_all")
                Base.metadata.create_all(self.sync_engine)
                return

            # Create Alembic config
            alembic_cfg = Config(alembic_ini)
            alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

            # Run migrations
            command.upgrade(alembic_cfg, "head")
            logger.info("Alembic migrations completed successfully")

        except Exception as e:
            logger.error(f"Alembic migration failed: {e}")
            logger.info("Falling back to SQLAlchemy create_all")
            Base.metadata.create_all(self.sync_engine)

    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status."""
        try:
            from alembic.config import Config
            from alembic.script import ScriptDirectory
            from alembic.runtime.migration import MigrationContext
            import os

            backend_dir = os.path.dirname(os.path.abspath(__file__))
            alembic_ini = os.path.join(backend_dir, "alembic.ini")

            if not os.path.exists(alembic_ini):
                return {"mode": "create_all", "alembic_available": False}

            alembic_cfg = Config(alembic_ini)
            script = ScriptDirectory.from_config(alembic_cfg)

            with self.sync_engine.connect() as conn:
                context = MigrationContext.configure(conn)
                current_rev = context.get_current_revision()

            head_rev = script.get_current_head()

            return {
                "mode": MIGRATION_MODE,
                "alembic_available": True,
                "current_revision": current_rev,
                "head_revision": head_rev,
                "is_up_to_date": current_rev == head_rev,
            }

        except Exception as e:
            return {
                "mode": MIGRATION_MODE,
                "alembic_available": False,
                "error": str(e),
            }

    @asynccontextmanager
    async def get_session(self):
        """Async context manager for database sessions"""
        async with self.AsyncSession() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # ==================== Journal Operations ====================

    async def create_journal(
        self,
        title: str,
        content: str,
        *,
        user_id: int,
        tags: Optional[List[str]] = None,
        folder_id: Optional[int] = None,
    ) -> int:
        """Create a new journal entry with embedding"""
        async with self.get_session() as session:
            # Generate embedding (if service available)
            embedding = None
            emb_service = self._get_embedding_service()
            if emb_service:
                embedding = emb_service.embed_text(f"{title} {content}")

            journal = Journal(
                title=title,
                content=content,
                tags={"tags": tags} if tags else None,
                folder_id=folder_id,
                user_id=user_id,
                embedding=embedding,
            )
            session.add(journal)
            await session.flush()
            return journal.id

    async def get_journals(
        self,
        *,
        user_id: int,
        folder_id: Optional[int] = None,
        search_query: Optional[str] = None,
    ) -> List[Dict]:
        """Get all journals for a user with optional filtering"""
        async with self.get_session() as session:
            stmt = (
                select(Journal, Folder.name.label("folder_name"))
                .outerjoin(Folder, Journal.folder_id == Folder.id)
                .where(Journal.user_id == user_id)
                .where(Journal.is_deleted == False)
            )

            if folder_id:
                stmt = stmt.where(Journal.folder_id == folder_id)

            if search_query:
                search_pattern = f"%{search_query}%"
                stmt = stmt.where(
                    or_(
                        Journal.title.ilike(search_pattern),
                        Journal.content.ilike(search_pattern),
                    )
                )

            stmt = stmt.order_by(Journal.updated_at.desc())
            result = await session.execute(stmt)

            journals = []
            for row in result:
                journal = row[0]
                journals.append({
                    "id": journal.id,
                    "title": journal.title,
                    "content": journal.content,
                    "tags": journal.tags.get("tags", []) if journal.tags else [],
                    "folder_id": journal.folder_id,
                    "folder_name": row.folder_name,
                    "user_id": journal.user_id,
                    "created_at": str(journal.created_at),
                    "updated_at": str(journal.updated_at),
                })

            return journals

    async def update_journal(
        self,
        journal_id: int,
        *,
        user_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        folder_id: Optional[int] = None,
    ) -> bool:
        """Update an existing journal"""
        async with self.get_session() as session:
            journal = await session.get(Journal, journal_id)
            if not journal or journal.user_id != user_id:
                return False

            if title is not None:
                journal.title = title
            if content is not None:
                journal.content = content
            if tags is not None:
                journal.tags = {"tags": tags}
            if folder_id is not None:
                journal.folder_id = folder_id

            # Update embedding if content changed (if service available)
            if title is not None or content is not None:
                emb_service = self._get_embedding_service()
                if emb_service:
                    journal.embedding = emb_service.embed_text(
                        f"{journal.title} {journal.content}"
                    )

            return True

    async def delete_journal(self, journal_id: int, *, user_id: int) -> bool:
        """Soft delete a journal entry"""
        async with self.get_session() as session:
            journal = await session.get(Journal, journal_id)
            if journal and journal.user_id == user_id:
                journal.is_deleted = True
                return True
            return False

    # ==================== Folder Operations ====================

    async def create_folder(
        self,
        name: str,
        *,
        user_id: int,
        description: Optional[str] = None,
        color: str = "#8A2BE2",
    ) -> int:
        """Create a new folder"""
        async with self.get_session() as session:
            folder = Folder(name=name, user_id=user_id)
            session.add(folder)
            await session.flush()
            return folder.id

    async def get_folders(self, *, user_id: int) -> List[Dict]:
        """Get all folders for a user with journal counts"""
        async with self.get_session() as session:
            stmt = (
                select(
                    Folder,
                    func.count(Journal.id).label("journal_count"),
                )
                .outerjoin(Journal, and_(
                    Folder.id == Journal.folder_id,
                    Journal.is_deleted == False
                ))
                .where(Folder.user_id == user_id)
                .group_by(Folder.id)
                .order_by(Folder.created_at.desc())
            )

            result = await session.execute(stmt)

            folders = []
            for row in result:
                folder = row[0]
                folders.append({
                    "id": folder.id,
                    "name": folder.name,
                    "user_id": folder.user_id,
                    "journal_count": row.journal_count,
                    "created_at": str(folder.created_at),
                })

            return folders

    async def update_folder(
        self,
        folder_id: int,
        *,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
    ) -> bool:
        """Update an existing folder"""
        async with self.get_session() as session:
            folder = await session.get(Folder, folder_id)
            if not folder or folder.user_id != user_id:
                return False

            if name is not None:
                folder.name = name

            return True

    async def delete_folder(self, folder_id: int, *, user_id: int) -> bool:
        """Delete a folder and unlink its journals"""
        async with self.get_session() as session:
            # Unlink journals
            await session.execute(
                text("UPDATE journals SET folder_id = NULL WHERE folder_id = :fid"),
                {"fid": folder_id},
            )

            folder = await session.get(Folder, folder_id)
            if folder and folder.user_id == user_id:
                await session.delete(folder)
                return True
            return False

    # ==================== Conversation Operations ====================

    async def create_conversation(
        self,
        session_id: str,
        *,
        user_id: int,
        title: Optional[str] = None,
    ) -> int:
        """Create a new conversation record"""
        async with self.get_session() as session:
            conv = Conversation(
                session_id=session_id,
                title=title,
                user_id=user_id,
            )
            session.add(conv)
            await session.flush()
            return conv.id

    async def get_or_create_conversation(
        self, session_id: str, *, user_id: int
    ) -> int:
        """Get existing conversation or create new one"""
        async with self.get_session() as session:
            stmt = select(Conversation).where(
                Conversation.session_id == session_id,
                Conversation.user_id == user_id,
            )
            result = await session.execute(stmt)
            conv = result.scalar_one_or_none()

            if conv:
                return conv.id

            # Create new
            conv = Conversation(session_id=session_id, user_id=user_id)
            session.add(conv)
            await session.flush()
            return conv.id

    async def add_chat_message(
        self,
        session_id: str,
        sender: str,
        message: str,
        *,
        user_id: int,
    ) -> int:
        """Add a message to the conversation with embedding"""
        async with self.get_session() as session:
            # Get or create conversation
            stmt = select(Conversation).where(
                Conversation.session_id == session_id,
                Conversation.user_id == user_id,
            )
            result = await session.execute(stmt)
            conv = result.scalar_one_or_none()

            if not conv:
                conv = Conversation(
                    session_id=session_id,
                    user_id=user_id,
                )
                session.add(conv)
                await session.flush()

            # Generate embedding (if service available)
            embedding = None
            emb_service = self._get_embedding_service()
            if emb_service:
                embedding = emb_service.embed_text(message)

            # Add message
            chat_msg = ChatMessage(
                conversation_id=conv.id,
                session_id=session_id,
                sender=sender,
                message=message,
                embedding=embedding,
            )
            session.add(chat_msg)

            # Update conversation title if first user message
            if sender == "user" and not conv.title:
                conv.title = message[:50] + ("..." if len(message) > 50 else "")

            await session.flush()
            return conv.id

    async def get_conversation_messages(
        self, session_id: str, *, user_id: int
    ) -> List[Dict]:
        """Get all messages for a conversation by session_id"""
        async with self.get_session() as session:
            stmt = (
                select(ChatMessage)
                .join(Conversation)
                .where(
                    ChatMessage.session_id == session_id,
                    Conversation.user_id == user_id,
                )
                .order_by(ChatMessage.timestamp.asc())
            )

            result = await session.execute(stmt)
            messages = []

            for row in result.scalars():
                messages.append({
                    "id": row.id,
                    "role": row.sender,
                    "content": row.message,
                    "created_at": str(row.timestamp),
                })

            return messages

    async def get_conversation_session_id(
        self, conversation_id: int, *, user_id: int
    ) -> Optional[str]:
        """Look up a conversation's real session_id from its numeric id -
        needed by the frontend for share/export calls, which key off
        session_id, not the conversation's primary key."""
        async with self.get_session() as session:
            stmt = select(Conversation.session_id).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_conversation_messages_by_id(
        self, conversation_id: int, *, user_id: int
    ) -> List[Dict]:
        """Get all messages for a conversation by conversation ID"""
        async with self.get_session() as session:
            stmt = (
                select(ChatMessage)
                .join(Conversation)
                .where(
                    ChatMessage.conversation_id == conversation_id,
                    Conversation.user_id == user_id,
                )
                .order_by(ChatMessage.timestamp.asc())
            )

            result = await session.execute(stmt)
            messages = []

            for row in result.scalars():
                messages.append({
                    "id": row.id,
                    "role": row.sender,
                    "content": row.message,
                    "created_at": str(row.timestamp),
                })

            return messages

    async def get_conversations(self, *, user_id: int, limit: int = 50) -> List[Dict]:
        """Get all conversations for sidebar display"""
        async with self.get_session() as session:
            stmt = (
                select(
                    Conversation,
                    func.count(ChatMessage.id).label("message_count"),
                )
                .outerjoin(ChatMessage)
                .where(Conversation.user_id == user_id)
                .group_by(Conversation.id)
                .having(func.count(ChatMessage.id) > 0)
                .order_by(Conversation.updated_at.desc())
                .limit(limit)
            )

            result = await session.execute(stmt)
            conversations = []

            for row in result:
                conv = row[0]
                conversations.append({
                    "id": conv.id,
                    "session_id": conv.session_id,
                    "title": conv.title,
                    "message_count": row.message_count,
                    "created_at": str(conv.created_at),
                    "updated_at": str(conv.updated_at),
                })

            return conversations

    async def update_conversation_title(
        self, conversation_id: int, title: str, *, user_id: int
    ) -> bool:
        """Update conversation title"""
        async with self.get_session() as session:
            conv = await session.get(Conversation, conversation_id)
            if conv and conv.user_id == user_id:
                conv.title = title
                return True
            return False

    async def delete_conversation(
        self, conversation_id: int, *, user_id: int, permanent: bool = False
    ) -> bool:
        """Delete a conversation"""
        async with self.get_session() as session:
            conv = await session.get(Conversation, conversation_id)
            if not conv or conv.user_id != user_id:
                return False

            if permanent:
                await session.delete(conv)
            else:
                # Soft delete by removing messages
                await session.execute(
                    text("DELETE FROM chat_messages WHERE conversation_id = :cid"),
                    {"cid": conversation_id},
                )
                await session.delete(conv)

            return True

    async def clear_conversation(self, session_id: str, *, user_id: int) -> bool:
        """Clear/delete a conversation and all its messages"""
        async with self.get_session() as session:
            stmt = select(Conversation).where(
                Conversation.session_id == session_id,
                Conversation.user_id == user_id,
            )
            result = await session.execute(stmt)
            conv = result.scalar_one_or_none()

            if conv:
                await session.delete(conv)
                return True
            return False

    # ==================== Learning State Operations ====================

    async def get_learning_state(self, session_id: str) -> Optional[Dict]:
        """Get learning state for a session"""
        async with self.get_session() as session:
            stmt = select(LearningState).where(LearningState.session_id == session_id)
            result = await session.execute(stmt)
            state = result.scalar_one_or_none()

            if state:
                return state.to_dict()
            return None

    async def save_learning_state(
        self, session_id: str, state_data: Dict, *, user_id: int
    ) -> None:
        """Save or update learning state"""
        async with self.get_session() as session:
            stmt = select(LearningState).where(LearningState.session_id == session_id)
            result = await session.execute(stmt)
            state = result.scalar_one_or_none()

            if state:
                # Update existing
                state.topic = state_data.get("topic")
                state.turn_count = state_data.get("turn_count", 0)
                state.confusion_count = state_data.get("confusion_count", 0)
                state.understanding_signals = state_data.get("understanding_signals", 0)
                state.last_state = state_data.get("last_state", "initial")
                state.topics_discussed = state_data.get("topics_discussed", [])
                state.key_discoveries = state_data.get("key_discoveries", [])
                state.content_richness = state_data.get("content_richness", "empty")
                state.content_score = state_data.get("content_score", 0.0)
                state.extracted_concepts = state_data.get("extracted_concepts", [])
                state.conversation_context = state_data.get("conversation_context", [])
            else:
                # Create new
                state = LearningState.from_dict(session_id, state_data, user_id)
                session.add(state)

    # ==================== Statistics ====================

    async def get_user_stats(self, user_id: Optional[int] = None) -> Dict:
        """
        Get statistics. With a user_id, returns that user's counts (used by the
        authenticated /stats endpoint). Without one, returns global counts across
        all users - used only by the unauthenticated /health check, which needs
        to stay reachable for PaaS health probes without a login.
        """
        async with self.get_session() as session:
            stats = {}

            journal_stmt = select(func.count(Journal.id)).where(Journal.is_deleted == False)
            folder_stmt = select(func.count(Folder.id))
            conversation_stmt = select(func.count(Conversation.id))

            if user_id is not None:
                journal_stmt = journal_stmt.where(Journal.user_id == user_id)
                folder_stmt = folder_stmt.where(Folder.user_id == user_id)
                conversation_stmt = conversation_stmt.where(Conversation.user_id == user_id)

            stats["total_journals"] = (await session.execute(journal_stmt)).scalar() or 0
            stats["total_folders"] = (await session.execute(folder_stmt)).scalar() or 0
            stats["total_conversations"] = (await session.execute(conversation_stmt)).scalar() or 0

            return stats


# Singleton instance
_db_manager: Optional[DatabaseManager] = None


def get_database() -> DatabaseManager:
    """Get or create the database manager singleton"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.init_database()
    return _db_manager
