"""
Migration Service for RAG System
Migrates existing journals and conversations to the new document/chunk structure
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Document, Chunk, Journal, Conversation, ChatMessage,
    SourceType, DocumentStatus
)
from services.ingestion_service import get_ingestion_service
from config import settings

logger = logging.getLogger(__name__)


class MigrationService:
    """
    Service for migrating existing data to the new RAG system.

    Handles:
    - Journal to Document/Chunk migration
    - Conversation to Document/Chunk migration
    - Batch processing with progress tracking
    """

    def __init__(self):
        self._ingestion_service = None

    @property
    def ingestion_service(self):
        """Lazy load ingestion service"""
        if self._ingestion_service is None:
            self._ingestion_service = get_ingestion_service()
        return self._ingestion_service

    async def migrate_journal(
        self,
        db: AsyncSession,
        journal: Journal,
        generate_chunks: bool = True
    ) -> Optional[Document]:
        """
        Migrate a single journal to the document/chunk structure.

        Args:
            db: Database session
            journal: Journal to migrate
            generate_chunks: Whether to generate chunks and embeddings

        Returns:
            Created Document or None if failed
        """
        try:
            # Check if already migrated
            existing = await db.execute(
                select(Document).where(
                    Document.source_type == SourceType.JOURNAL,
                    Document.source_id == journal.id
                )
            )
            if existing.scalar_one_or_none():
                logger.info(f"Journal {journal.id} already migrated, skipping")
                return None

            # Prepare metadata
            metadata = {
                "original_tags": journal.tags,
                "folder_id": journal.folder_id,
                "word_count": len(journal.content.split()) if journal.content else 0,
            }

            if generate_chunks:
                # Generate summary, chunks, and embeddings
                summary, summary_embedding, chunks, chunk_embeddings = \
                    self.ingestion_service.process_text_content(
                        content=journal.content,
                        title=journal.title,
                        metadata=metadata
                    )
            else:
                summary = self.ingestion_service.generate_summary(journal.content)
                summary_embedding = None
                chunks = []
                chunk_embeddings = []

            # Create document
            document = Document(
                user_id=journal.user_id,
                title=journal.title,
                content=journal.content,
                source_type=SourceType.JOURNAL,
                source_id=journal.id,
                document_metadata=metadata,
                summary=summary,
                embedding=summary_embedding,
                status=DocumentStatus.COMPLETED if generate_chunks else DocumentStatus.PENDING,
                created_at=journal.created_at,
                updated_at=journal.updated_at,
            )
            db.add(document)
            await db.flush()

            # Create chunks
            if generate_chunks and chunks:
                for chunk_data, embedding in zip(chunks, chunk_embeddings):
                    chunk = Chunk(
                        document_id=document.id,
                        chunk_index=chunk_data.chunk_index,
                        content=chunk_data.content,
                        chunk_metadata=chunk_data.metadata,
                        embedding=embedding,
                    )
                    db.add(chunk)

            await db.commit()
            logger.info(f"Migrated journal {journal.id} -> document {document.id} with {len(chunks)} chunks")
            return document

        except Exception as e:
            await db.rollback()
            logger.error(f"Error migrating journal {journal.id}: {e}")
            return None

    async def migrate_conversation(
        self,
        db: AsyncSession,
        conversation: Conversation,
        generate_chunks: bool = True
    ) -> Optional[Document]:
        """
        Migrate a conversation to the document/chunk structure.

        Combines all messages in the conversation into a single document.

        Args:
            db: Database session
            conversation: Conversation to migrate
            generate_chunks: Whether to generate chunks and embeddings

        Returns:
            Created Document or None if failed
        """
        try:
            # Check if already migrated
            existing = await db.execute(
                select(Document).where(
                    Document.source_type == SourceType.CHAT,
                    Document.source_id == conversation.id
                )
            )
            if existing.scalar_one_or_none():
                logger.info(f"Conversation {conversation.id} already migrated, skipping")
                return None

            # Get all messages for this conversation
            messages_result = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.conversation_id == conversation.id)
                .order_by(ChatMessage.timestamp)
            )
            messages = messages_result.scalars().all()

            if not messages:
                logger.info(f"Conversation {conversation.id} has no messages, skipping")
                return None

            # Combine messages into document content
            content_parts = []
            for msg in messages:
                role = "User" if msg.sender == "user" else "Assistant"
                content_parts.append(f"[{role}]: {msg.message}")

            content = "\n\n".join(content_parts)

            # Prepare metadata
            metadata = {
                "session_id": messages[0].session_id if messages else None,
                "message_count": len(messages),
                "word_count": len(content.split()),
            }

            if generate_chunks:
                # Generate summary, chunks, and embeddings
                summary, summary_embedding, chunks, chunk_embeddings = \
                    self.ingestion_service.process_text_content(
                        content=content,
                        title=conversation.title or f"Conversation {conversation.id}",
                        metadata=metadata
                    )
            else:
                summary = self.ingestion_service.generate_summary(content)
                summary_embedding = None
                chunks = []
                chunk_embeddings = []

            # Create document
            document = Document(
                user_id=conversation.user_id,
                title=conversation.title or f"Conversation {conversation.id}",
                content=content,
                source_type=SourceType.CHAT,
                source_id=conversation.id,
                document_metadata=metadata,
                summary=summary,
                embedding=summary_embedding,
                status=DocumentStatus.COMPLETED if generate_chunks else DocumentStatus.PENDING,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
            )
            db.add(document)
            await db.flush()

            # Create chunks
            if generate_chunks and chunks:
                for chunk_data, embedding in zip(chunks, chunk_embeddings):
                    chunk = Chunk(
                        document_id=document.id,
                        chunk_index=chunk_data.chunk_index,
                        content=chunk_data.content,
                        chunk_metadata=chunk_data.metadata,
                        embedding=embedding,
                    )
                    db.add(chunk)

            await db.commit()
            logger.info(f"Migrated conversation {conversation.id} -> document {document.id} with {len(chunks)} chunks")
            return document

        except Exception as e:
            await db.rollback()
            logger.error(f"Error migrating conversation {conversation.id}: {e}")
            return None

    async def migrate_all_journals(
        self,
        db: AsyncSession,
        batch_size: int = 50,
        generate_chunks: bool = True
    ) -> Dict[str, Any]:
        """
        Migrate all journals to the new structure.

        Args:
            db: Database session
            batch_size: Number of journals to process per batch
            generate_chunks: Whether to generate chunks and embeddings

        Returns:
            Migration statistics
        """
        logger.info("Starting journal migration...")

        stats = {
            "total": 0,
            "migrated": 0,
            "skipped": 0,
            "failed": 0,
        }

        # Count total journals
        count_result = await db.execute(
            select(func.count(Journal.id)).where(Journal.is_deleted == False)
        )
        stats["total"] = count_result.scalar()

        # Process in batches
        offset = 0
        while True:
            journals_result = await db.execute(
                select(Journal)
                .where(Journal.is_deleted == False)
                .offset(offset)
                .limit(batch_size)
            )
            journals = journals_result.scalars().all()

            if not journals:
                break

            for journal in journals:
                result = await self.migrate_journal(db, journal, generate_chunks)
                if result:
                    stats["migrated"] += 1
                elif result is None:
                    stats["skipped"] += 1
                else:
                    stats["failed"] += 1

            offset += batch_size
            logger.info(f"Migrated {offset} journals...")

        logger.info(f"Journal migration complete: {stats}")
        return stats

    async def migrate_all_conversations(
        self,
        db: AsyncSession,
        batch_size: int = 50,
        generate_chunks: bool = True
    ) -> Dict[str, Any]:
        """
        Migrate all conversations to the new structure.

        Args:
            db: Database session
            batch_size: Number of conversations to process per batch
            generate_chunks: Whether to generate chunks and embeddings

        Returns:
            Migration statistics
        """
        logger.info("Starting conversation migration...")

        stats = {
            "total": 0,
            "migrated": 0,
            "skipped": 0,
            "failed": 0,
        }

        # Count total conversations
        count_result = await db.execute(
            select(func.count(Conversation.id))
        )
        stats["total"] = count_result.scalar()

        # Process in batches
        offset = 0
        while True:
            conversations_result = await db.execute(
                select(Conversation)
                .offset(offset)
                .limit(batch_size)
            )
            conversations = conversations_result.scalars().all()

            if not conversations:
                break

            for conversation in conversations:
                result = await self.migrate_conversation(db, conversation, generate_chunks)
                if result:
                    stats["migrated"] += 1
                elif result is None:
                    stats["skipped"] += 1
                else:
                    stats["failed"] += 1

            offset += batch_size
            logger.info(f"Migrated {offset} conversations...")

        logger.info(f"Conversation migration complete: {stats}")
        return stats

    async def run_full_migration(
        self,
        db: AsyncSession,
        batch_size: int = 50,
        generate_chunks: bool = True
    ) -> Dict[str, Any]:
        """
        Run full migration of journals and conversations.

        Args:
            db: Database session
            batch_size: Number of items to process per batch
            generate_chunks: Whether to generate chunks and embeddings

        Returns:
            Complete migration statistics
        """
        logger.info("Starting full migration...")

        journal_stats = await self.migrate_all_journals(db, batch_size, generate_chunks)
        conversation_stats = await self.migrate_all_conversations(db, batch_size, generate_chunks)

        return {
            "journals": journal_stats,
            "conversations": conversation_stats,
            "total_migrated": journal_stats["migrated"] + conversation_stats["migrated"],
            "total_failed": journal_stats["failed"] + conversation_stats["failed"],
        }

    async def verify_migration(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Verify migration integrity.

        Args:
            db: Database session

        Returns:
            Verification results
        """
        results = {
            "documents": {},
            "chunks": {},
            "issues": [],
        }

        # Count documents by source type
        for source_type in SourceType:
            count_result = await db.execute(
                select(func.count(Document.id)).where(
                    Document.source_type == source_type,
                    Document.is_deleted == False
                )
            )
            results["documents"][source_type.value] = count_result.scalar()

        # Count chunks
        chunk_count = await db.execute(select(func.count(Chunk.id)))
        results["chunks"]["total"] = chunk_count.scalar()

        # Check for documents without chunks
        orphan_docs = await db.execute(
            select(Document)
            .where(
                Document.status == DocumentStatus.COMPLETED,
                ~Document.id.in_(select(Chunk.document_id).distinct())
            )
        )
        orphan_list = orphan_docs.scalars().all()
        if orphan_list:
            results["issues"].append({
                "type": "documents_without_chunks",
                "count": len(orphan_list),
                "document_ids": [d.id for d in orphan_list[:10]],  # First 10
            })

        # Check for documents without embeddings
        no_embedding = await db.execute(
            select(func.count(Document.id)).where(
                Document.status == DocumentStatus.COMPLETED,
                Document.embedding == None
            )
        )
        no_embedding_count = no_embedding.scalar()
        if no_embedding_count > 0:
            results["issues"].append({
                "type": "documents_without_embeddings",
                "count": no_embedding_count,
            })

        return results


# Singleton instance
_migration_service: Optional[MigrationService] = None


def get_migration_service() -> MigrationService:
    """Get or create the migration service singleton"""
    global _migration_service
    if _migration_service is None:
        _migration_service = MigrationService()
    return _migration_service
