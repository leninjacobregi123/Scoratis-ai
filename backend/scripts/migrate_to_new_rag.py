#!/usr/bin/env python3
"""
Migration Script: Migrate to New RAG System
Converts existing conversations to the new document/chunk structure

Usage:
    python scripts/migrate_to_new_rag.py [--dry-run] [--batch-size N] [--skip-embeddings]

Options:
    --dry-run         Show what would be migrated without making changes
    --batch-size N    Number of items to process per batch (default: 50)
    --skip-embeddings Skip embedding generation (process later with Celery)
"""

import asyncio
import argparse
import sys
import os
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import settings
from database import get_database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def check_prerequisites():
    """Check that all prerequisites are met"""
    logger.info("Checking prerequisites...")

    # Check database connection
    try:
        db = get_database()
        async with db.get_session() as session:
            result = await session.execute(text("SELECT 1"))
            logger.info("Database connection: OK")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

    # Check required extensions
    try:
        async with db.get_session() as session:
            result = await session.execute(text(
                "SELECT extname FROM pg_extension WHERE extname IN ('vector', 'pg_trgm')"
            ))
            extensions = [row[0] for row in result.fetchall()]

            if 'vector' not in extensions:
                logger.error("pgvector extension not installed")
                return False
            logger.info("pgvector extension: OK")

            if 'pg_trgm' not in extensions:
                logger.warning("pg_trgm extension not installed - will create it")
                await session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
                await session.commit()
            logger.info("pg_trgm extension: OK")

    except Exception as e:
        logger.error(f"Extension check failed: {e}")
        return False

    return True


async def create_tables():
    """Create new tables if they don't exist"""
    logger.info("Creating tables...")

    db = get_database()
    async with db.get_session() as session:
        # Check if tables exist
        result = await session.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('documents', 'chunks')
        """))
        existing_tables = [row[0] for row in result.fetchall()]

        if 'documents' in existing_tables and 'chunks' in existing_tables:
            logger.info("Tables already exist")
            return True

        # Create tables using SQLAlchemy models
        from models import Base, Document, Chunk

        # Use sync engine for table creation
        sync_engine = create_engine(settings.DATABASE_URL)
        Base.metadata.create_all(sync_engine, tables=[Document.__table__, Chunk.__table__])
        sync_engine.dispose()

        logger.info("Tables created successfully")
        return True


async def create_indexes():
    """Create indexes for new tables"""
    logger.info("Creating indexes...")

    db = get_database()
    async with db.get_session() as session:
        try:
            # HNSW index for documents
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_documents_embedding_hnsw
                ON documents USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """))

            # HNSW index for chunks
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
                ON chunks USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """))

            # GIN index for full-text search on documents
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_documents_content_fts
                ON documents USING gin (content gin_trgm_ops)
            """))

            # GIN index for full-text search on chunks
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_chunks_content_fts
                ON chunks USING gin (content gin_trgm_ops)
            """))

            await session.commit()
            logger.info("Indexes created successfully")
            return True

        except Exception as e:
            await session.rollback()
            logger.error(f"Index creation failed: {e}")
            return False


async def get_migration_stats():
    """Get statistics about what needs to be migrated"""
    db = get_database()
    async with db.get_session() as session:
        # Count conversations
        conversations_result = await session.execute(text(
            "SELECT COUNT(*) FROM conversations"
        ))
        conversation_count = conversations_result.scalar()

        # Count existing documents
        try:
            documents_result = await session.execute(text(
                "SELECT COUNT(*) FROM documents WHERE is_deleted = false"
            ))
            document_count = documents_result.scalar()
        except:
            document_count = 0

        # Count existing chunks
        try:
            chunks_result = await session.execute(text(
                "SELECT COUNT(*) FROM chunks"
            ))
            chunk_count = chunks_result.scalar()
        except:
            chunk_count = 0

        return {
            "conversations": conversation_count,
            "existing_documents": document_count,
            "existing_chunks": chunk_count,
        }


async def run_migration(
    dry_run: bool = False,
    batch_size: int = 50,
    skip_embeddings: bool = False
):
    """Run the full migration"""
    logger.info("=" * 60)
    logger.info("RAG System Migration")
    logger.info("=" * 60)

    if dry_run:
        logger.info("*** DRY RUN MODE - No changes will be made ***")

    # Check prerequisites
    if not await check_prerequisites():
        logger.error("Prerequisites check failed. Aborting migration.")
        return False

    # Get stats before migration
    stats = await get_migration_stats()
    logger.info(f"\nMigration Statistics:")
    logger.info(f"  - Conversations to migrate: {stats['conversations']}")
    logger.info(f"  - Existing documents: {stats['existing_documents']}")
    logger.info(f"  - Existing chunks: {stats['existing_chunks']}")

    if dry_run:
        logger.info("\n*** DRY RUN COMPLETE - No changes made ***")
        return True

    # Create tables
    if not await create_tables():
        logger.error("Table creation failed. Aborting migration.")
        return False

    # Create indexes
    if not await create_indexes():
        logger.warning("Index creation had issues, continuing anyway...")

    # Run migration
    logger.info("\nStarting data migration...")

    from services.migration_service import get_migration_service
    migration_service = get_migration_service()

    db = get_database()
    async with db.get_session() as session:
        results = await migration_service.run_full_migration(
            db=session,
            batch_size=batch_size,
            generate_chunks=not skip_embeddings
        )

    logger.info("\n" + "=" * 60)
    logger.info("Migration Complete!")
    logger.info("=" * 60)
    logger.info(f"\nResults:")
    logger.info(f"  Conversations:")
    logger.info(f"    - Total: {results['conversations']['total']}")
    logger.info(f"    - Migrated: {results['conversations']['migrated']}")
    logger.info(f"    - Skipped: {results['conversations']['skipped']}")
    logger.info(f"    - Failed: {results['conversations']['failed']}")
    logger.info(f"\n  Summary:")
    logger.info(f"    - Total migrated: {results['total_migrated']}")
    logger.info(f"    - Total failed: {results['total_failed']}")

    # Verify migration
    logger.info("\nVerifying migration...")
    async with db.get_session() as session:
        verification = await migration_service.verify_migration(session)

    logger.info(f"\nVerification Results:")
    logger.info(f"  Documents by source:")
    for source, count in verification['documents'].items():
        logger.info(f"    - {source}: {count}")
    logger.info(f"  Total chunks: {verification['chunks']['total']}")

    if verification['issues']:
        logger.warning(f"\n  Issues found:")
        for issue in verification['issues']:
            logger.warning(f"    - {issue['type']}: {issue.get('count', 'N/A')}")
    else:
        logger.info("  No issues found!")

    if skip_embeddings:
        logger.info("\n*** NOTE: Embeddings were skipped. ***")
        logger.info("Run the following to generate embeddings:")
        logger.info("  celery -A celery_app worker --loglevel=info")
        logger.info("  Then use the API to trigger embedding generation.")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Migrate existing data to the new RAG system"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of items to process per batch (default: 50)"
    )
    parser.add_argument(
        "--skip-embeddings",
        action="store_true",
        help="Skip embedding generation (process later with Celery)"
    )

    args = parser.parse_args()

    success = asyncio.run(run_migration(
        dry_run=args.dry_run,
        batch_size=args.batch_size,
        skip_embeddings=args.skip_embeddings
    ))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
