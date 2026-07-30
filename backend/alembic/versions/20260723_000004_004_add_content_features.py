"""Add content features: quizzes, subject progress, spaced-repetition review, transcript sharing

Revision ID: 004
Revises: 003
Create Date: 2026-07-23

Adds the tables backing Phase 3's four learning features:
- quizzes / quiz_questions / quiz_attempts: generated practice problems
- subject_progress: one row per (user, subject), upserted incrementally
- review_items: SM-2 spaced-repetition queue
- conversations.share_token: unauthenticated read-only transcript sharing
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE review_source_type AS ENUM ('key_discovery', 'quiz_question');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.create_table(
        'quizzes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(100), nullable=False),
        sa.Column('topic', sa.String(500), nullable=False),
        sa.Column('source_document_ids', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_quizzes_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_quizzes'),
    )
    op.create_index('ix_quizzes_id', 'quizzes', ['id'])
    op.create_index('ix_quizzes_user_id', 'quizzes', ['user_id'])
    op.create_index('ix_quizzes_subject', 'quizzes', ['subject'])

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

    op.create_table(
        'subject_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(100), nullable=False),
        sa.Column('mastery_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('total_turns', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_sessions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('quizzes_taken', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('quiz_average', sa.Float(), nullable=False, server_default='0'),
        sa.Column('scaffold_step', sa.String(50), nullable=True),
        sa.Column('last_active_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_subject_progress_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_subject_progress'),
        sa.UniqueConstraint('user_id', 'subject', name='uq_subject_progress_user_subject'),
    )
    op.create_index('ix_subject_progress_id', 'subject_progress', ['id'])
    op.create_index('ix_subject_progress_user_id', 'subject_progress', ['user_id'])
    op.create_index('ix_subject_progress_subject', 'subject_progress', ['subject'])

    op.create_table(
        'review_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(100), nullable=False),
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
    op.create_index('ix_review_items_subject', 'review_items', ['subject'])
    op.create_index('idx_review_items_user_due', 'review_items', ['user_id', 'due_at'])

    op.add_column('conversations', sa.Column('share_token', sa.String(64), nullable=True))
    op.create_index('ix_conversations_share_token', 'conversations', ['share_token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_conversations_share_token', table_name='conversations')
    op.drop_column('conversations', 'share_token')

    op.drop_index('idx_review_items_user_due', table_name='review_items')
    op.drop_index('ix_review_items_subject', table_name='review_items')
    op.drop_index('ix_review_items_user_id', table_name='review_items')
    op.drop_index('ix_review_items_id', table_name='review_items')
    op.drop_table('review_items')

    op.drop_index('ix_subject_progress_subject', table_name='subject_progress')
    op.drop_index('ix_subject_progress_user_id', table_name='subject_progress')
    op.drop_index('ix_subject_progress_id', table_name='subject_progress')
    op.drop_table('subject_progress')

    op.drop_index('ix_quiz_attempts_user_id', table_name='quiz_attempts')
    op.drop_index('ix_quiz_attempts_quiz_id', table_name='quiz_attempts')
    op.drop_index('ix_quiz_attempts_id', table_name='quiz_attempts')
    op.drop_table('quiz_attempts')

    op.drop_index('ix_quiz_questions_quiz_id', table_name='quiz_questions')
    op.drop_index('ix_quiz_questions_id', table_name='quiz_questions')
    op.drop_table('quiz_questions')

    op.drop_index('ix_quizzes_subject', table_name='quizzes')
    op.drop_index('ix_quizzes_user_id', table_name='quizzes')
    op.drop_index('ix_quizzes_id', table_name='quizzes')
    op.drop_table('quizzes')

    op.execute("DROP TYPE IF EXISTS review_source_type")
