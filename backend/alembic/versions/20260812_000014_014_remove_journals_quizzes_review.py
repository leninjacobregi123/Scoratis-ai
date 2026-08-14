"""Remove Journals, Quizzes, and Review (spaced-repetition) features entirely

Revision ID: 014
Revises: 013
Create Date: 2026-08-12

Journals, Quizzes, and spaced-repetition Review have been fully removed from
the product (backend routes, models, agent tools, and frontend UI already
deleted in this change) - this drops their tables, indexes, and the
review_source_type enum.

`folders` existed only to organize journal entries - grepping the codebase
before writing this migration confirmed no other feature (documents
included) ever referenced Folder/folder_id - so it's dropped too rather than
left behind as dead schema.

Every drop uses `IF EXISTS`/`DROP INDEX IF EXISTS`, same reasoning as
migration 008: some of these indexes were declared on the SQLAlchemy models
via Index(...)/index=True but only ever materialized via create_all() on
some environments, so their actual presence drifts across databases (see
migration 011's docstring for a concrete example of this same drift on the
journals table). Table drops cascade their own FK constraints automatically;
the explicit index drops just keep this safe to run regardless of which
indexes a given database actually has.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision: str = '014'
down_revision: Union[str, None] = '013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- review_items (SM-2 spaced-repetition queue) ---
    op.execute('DROP INDEX IF EXISTS idx_review_items_user_due')
    op.execute('DROP INDEX IF EXISTS ix_review_items_user_id')
    op.execute('DROP INDEX IF EXISTS ix_review_items_id')
    op.execute('DROP TABLE IF EXISTS review_items')
    op.execute('DROP TYPE IF EXISTS review_source_type')

    # --- quiz_attempts / quiz_questions / quizzes (drop children before parent) ---
    op.execute('DROP INDEX IF EXISTS ix_quiz_attempts_user_id')
    op.execute('DROP INDEX IF EXISTS ix_quiz_attempts_quiz_id')
    op.execute('DROP INDEX IF EXISTS ix_quiz_attempts_id')
    op.execute('DROP TABLE IF EXISTS quiz_attempts')

    op.execute('DROP INDEX IF EXISTS ix_quiz_questions_quiz_id')
    op.execute('DROP INDEX IF EXISTS ix_quiz_questions_id')
    op.execute('DROP TABLE IF EXISTS quiz_questions')

    op.execute('DROP INDEX IF EXISTS ix_quizzes_user_id')
    op.execute('DROP INDEX IF EXISTS ix_quizzes_id')
    op.execute('DROP TABLE IF EXISTS quizzes')

    # --- journals (drop before folders, which it FKs to) ---
    op.execute('DROP INDEX IF EXISTS idx_journals_content_fts')
    op.execute('DROP INDEX IF EXISTS idx_journals_embedding_hnsw')
    op.execute('DROP INDEX IF EXISTS ix_journals_embedding')
    op.execute('DROP INDEX IF EXISTS ix_journals_user_id')
    op.execute('DROP INDEX IF EXISTS ix_journals_id')
    op.execute('DROP TABLE IF EXISTS journals')

    # --- folders (only ever organized journals - see docstring) ---
    op.execute('DROP INDEX IF EXISTS ix_folders_user_id')
    op.execute('DROP INDEX IF EXISTS ix_folders_id')
    op.execute('DROP TABLE IF EXISTS folders')


def downgrade() -> None:
    # --- folders ---
    op.create_table(
        'folders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_folders_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_folders'),
    )
    op.create_index('ix_folders_id', 'folders', ['id'])
    op.create_index('ix_folders_user_id', 'folders', ['user_id'])

    # --- journals ---
    op.create_table(
        'journals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('folder_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['folder_id'], ['folders.id'], name='fk_journals_folder_id_folders', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_journals_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_journals'),
    )
    op.create_index('ix_journals_id', 'journals', ['id'])
    op.create_index('ix_journals_user_id', 'journals', ['user_id'])
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_journals_embedding_hnsw
        ON journals USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_journals_content_fts
        ON journals USING gin (content gin_trgm_ops)
    """)

    # --- quizzes / quiz_questions / quiz_attempts ---
    op.create_table(
        'quizzes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('topic', sa.String(500), nullable=False),
        sa.Column('source_document_ids', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_quizzes_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_quizzes'),
    )
    op.create_index('ix_quizzes_id', 'quizzes', ['id'])
    op.create_index('ix_quizzes_user_id', 'quizzes', ['user_id'])

    op.create_table(
        'quiz_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quiz_id', sa.Integer(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('options', postgresql.JSONB(), nullable=False),
        sa.Column('correct_answer', sa.String(500), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('source_chunk_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], name='fk_quiz_questions_quiz_id_quizzes', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_chunk_id'], ['chunks.id'], name='fk_quiz_questions_source_chunk_id_chunks', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='pk_quiz_questions'),
    )
    op.create_index('ix_quiz_questions_id', 'quiz_questions', ['id'])
    op.create_index('ix_quiz_questions_quiz_id', 'quiz_questions', ['quiz_id'])

    op.create_table(
        'quiz_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quiz_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('answers', postgresql.JSONB(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], name='fk_quiz_attempts_quiz_id_quizzes', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_quiz_attempts_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_quiz_attempts'),
    )
    op.create_index('ix_quiz_attempts_id', 'quiz_attempts', ['id'])
    op.create_index('ix_quiz_attempts_quiz_id', 'quiz_attempts', ['quiz_id'])
    op.create_index('ix_quiz_attempts_user_id', 'quiz_attempts', ['user_id'])

    # --- review_items ---
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE review_source_type AS ENUM ('key_discovery', 'quiz_question');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.create_table(
        'review_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('concept', sa.String(1000), nullable=False),
        sa.Column(
            'source_type',
            postgresql.ENUM('key_discovery', 'quiz_question', name='review_source_type', create_type=False),
            nullable=False,
        ),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('ease_factor', sa.Float(), nullable=False, server_default='2.5'),
        sa.Column('interval_days', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('repetitions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('due_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_review_items_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_review_items'),
    )
    op.create_index('ix_review_items_id', 'review_items', ['id'])
    op.create_index('ix_review_items_user_id', 'review_items', ['user_id'])
    op.create_index('idx_review_items_user_due', 'review_items', ['user_id', 'due_at'])
