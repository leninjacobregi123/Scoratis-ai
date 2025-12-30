"""Initial database schema with pgvector support

Revision ID: 001
Revises:
Create Date: 2024-12-30

This migration creates the complete Scoratis database schema including:
- PostgreSQL extensions (pgvector, pg_trgm)
- All core tables (users, journals, conversations, etc.)
- RAG tables (documents, chunks) with vector embeddings
- Indexes including HNSW for vector similarity search
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================================
    # Step 1: Create PostgreSQL Extensions
    # ==========================================================================
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ==========================================================================
    # Step 2: Create Enum Types
    # ==========================================================================
    # Source type enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE sourcetype AS ENUM ('journal', 'chat', 'upload');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Document status enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE documentstatus AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Provider type enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE providertype AS ENUM (
                'openai', 'anthropic', 'google', 'ollama', 'groq',
                'mistral', 'cohere', 'together', 'openrouter', 'deepseek', 'xai'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # ==========================================================================
    # Step 3: Create Core Tables
    # ==========================================================================

    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_users'),
        sa.UniqueConstraint('username', name='uq_users_username'),
    )
    op.create_index('ix_users_id', 'users', ['id'])

    # Folders table
    op.create_table(
        'folders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(7), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_folders_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_folders'),
    )
    op.create_index('ix_folders_id', 'folders', ['id'])
    op.create_index('ix_folders_user_id', 'folders', ['user_id'])

    # Journals table
    op.create_table(
        'journals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('folder_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['folder_id'], ['folders.id'], name='fk_journals_folder_id_folders', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_journals_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_journals'),
    )
    op.create_index('ix_journals_id', 'journals', ['id'])
    op.create_index('ix_journals_user_id', 'journals', ['user_id'])

    # Conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=False, unique=True),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('subject', sa.String(100), nullable=True, server_default='general'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_conversations_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_conversations'),
    )
    op.create_index('ix_conversations_id', 'conversations', ['id'])
    op.create_index('ix_conversations_session_id', 'conversations', ['session_id'])
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])

    # Chat messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=False),
        sa.Column('sender', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], name='fk_chat_messages_conversation_id_conversations', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_chat_messages'),
    )
    op.create_index('ix_chat_messages_id', 'chat_messages', ['id'])
    op.create_index('ix_chat_messages_session_id', 'chat_messages', ['session_id'])
    op.create_index('ix_chat_messages_conversation_id', 'chat_messages', ['conversation_id'])

    # Learning states table
    op.create_table(
        'learning_states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=False, unique=True),
        sa.Column('subject', sa.String(100), nullable=True),
        sa.Column('state_data', postgresql.JSONB(), nullable=True),
        sa.Column('topics_discussed', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('key_discoveries', postgresql.JSONB(), nullable=True),
        sa.Column('misconceptions', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_learning_states_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_learning_states'),
    )
    op.create_index('ix_learning_states_id', 'learning_states', ['id'])
    op.create_index('ix_learning_states_session_id', 'learning_states', ['session_id'])

    # LLM provider configs table
    op.create_table(
        'llm_provider_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', postgresql.ENUM('openai', 'anthropic', 'google', 'ollama', 'groq', 'mistral', 'cohere', 'together', 'openrouter', 'deepseek', 'xai', name='providertype', create_type=False), nullable=False),
        sa.Column('api_key_encrypted', sa.Text(), nullable=True),
        sa.Column('model_id', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('base_url', sa.String(500), nullable=True),
        sa.Column('config', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_llm_provider_configs_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_llm_provider_configs'),
    )
    op.create_index('ix_llm_provider_configs_id', 'llm_provider_configs', ['id'])
    op.create_index('ix_llm_provider_configs_user_provider', 'llm_provider_configs', ['user_id', 'provider'])

    # ==========================================================================
    # Step 4: Create RAG Tables (Documents & Chunks)
    # ==========================================================================

    # Documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source_type', postgresql.ENUM('journal', 'chat', 'upload', name='sourcetype', create_type=False), nullable=False, server_default='upload'),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('file_path', sa.String(1000), nullable=True),
        sa.Column('file_type', sa.String(50), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('document_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('status', postgresql.ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='documentstatus', create_type=False), nullable=False, server_default='PENDING'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_documents_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_documents'),
    )
    op.create_index('ix_documents_id', 'documents', ['id'])
    op.create_index('ix_documents_user_id', 'documents', ['user_id'])
    op.create_index('idx_documents_user_status', 'documents', ['user_id', 'status'])
    op.create_index('idx_documents_source', 'documents', ['source_type', 'source_id'])

    # Chunks table
    op.create_table(
        'chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('chunk_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], name='fk_chunks_document_id_documents', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_chunks'),
    )
    op.create_index('ix_chunks_id', 'chunks', ['id'])
    op.create_index('ix_chunks_document_id', 'chunks', ['document_id'])
    op.create_index('idx_chunks_document_order', 'chunks', ['document_id', 'chunk_index'])

    # ==========================================================================
    # Step 5: Create HNSW Indexes for Vector Similarity Search
    # ==========================================================================

    # HNSW index for journals embedding
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_journals_embedding_hnsw
        ON journals USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # HNSW index for chat messages embedding
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_chat_messages_embedding_hnsw
        ON chat_messages USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # HNSW index for documents embedding (summary-level)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_embedding_hnsw
        ON documents USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # HNSW index for chunks embedding (granular search)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
        ON chunks USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # ==========================================================================
    # Step 6: Create Full-Text Search Indexes (GIN + pg_trgm)
    # ==========================================================================

    # Full-text search on documents content
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_content_fts
        ON documents USING gin (content gin_trgm_ops)
    """)

    # Full-text search on chunks content
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunks_content_fts
        ON chunks USING gin (content gin_trgm_ops)
    """)

    # Full-text search on journals content
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_journals_content_fts
        ON journals USING gin (content gin_trgm_ops)
    """)


def downgrade() -> None:
    # ==========================================================================
    # Drop indexes
    # ==========================================================================
    op.execute("DROP INDEX IF EXISTS idx_journals_content_fts")
    op.execute("DROP INDEX IF EXISTS idx_chunks_content_fts")
    op.execute("DROP INDEX IF EXISTS idx_documents_content_fts")
    op.execute("DROP INDEX IF EXISTS idx_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_documents_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_chat_messages_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_journals_embedding_hnsw")

    # ==========================================================================
    # Drop tables (in reverse order of creation due to foreign keys)
    # ==========================================================================
    op.drop_table('chunks')
    op.drop_table('documents')
    op.drop_table('llm_provider_configs')
    op.drop_table('learning_states')
    op.drop_table('chat_messages')
    op.drop_table('conversations')
    op.drop_table('journals')
    op.drop_table('folders')
    op.drop_table('users')

    # ==========================================================================
    # Drop enum types
    # ==========================================================================
    op.execute("DROP TYPE IF EXISTS providertype")
    op.execute("DROP TYPE IF EXISTS documentstatus")
    op.execute("DROP TYPE IF EXISTS sourcetype")

    # ==========================================================================
    # Drop extensions (optional - usually kept)
    # ==========================================================================
    # op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    # op.execute("DROP EXTENSION IF EXISTS vector")
