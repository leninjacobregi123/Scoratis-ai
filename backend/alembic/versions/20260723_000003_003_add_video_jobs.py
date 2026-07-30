"""Add video_jobs table for Celery-backed video generation

Revision ID: 003
Revises: 002
Create Date: 2026-07-23

Replaces the in-memory task-tracking dict in video_service.py
(VideoGenerationService.tasks) with real persistence, so generation state
survives worker restarts and is visible across multiple API/worker
processes. See backend/tasks/video_tasks.py for the Celery task that
writes to this table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE video_job_status AS ENUM ('pending', 'rendering', 'completed', 'failed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.create_table(
        'video_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('topic', sa.String(500), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('quality', sa.String(20), nullable=False, server_default='high'),
        sa.Column('duration_seconds', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('auto_generated', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('context', postgresql.JSONB(), nullable=True),
        sa.Column(
            'status',
            postgresql.ENUM('pending', 'rendering', 'completed', 'failed', name='video_job_status', create_type=False),
            nullable=False,
            server_default='pending',
        ),
        sa.Column('stage', sa.String(50), nullable=False, server_default='content'),
        sa.Column('progress_percent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('video_path', sa.String(1000), nullable=True),
        sa.Column('script', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_video_jobs_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_video_jobs'),
    )
    op.create_index('ix_video_jobs_id', 'video_jobs', ['id'])
    op.create_index('ix_video_jobs_user_id', 'video_jobs', ['user_id'])
    op.create_index('ix_video_jobs_session_id', 'video_jobs', ['session_id'])
    op.create_index('idx_video_jobs_user_status', 'video_jobs', ['user_id', 'status'])


def downgrade() -> None:
    op.drop_index('idx_video_jobs_user_status', table_name='video_jobs')
    op.drop_index('ix_video_jobs_session_id', table_name='video_jobs')
    op.drop_index('ix_video_jobs_user_id', table_name='video_jobs')
    op.drop_index('ix_video_jobs_id', table_name='video_jobs')
    op.drop_table('video_jobs')
    op.execute("DROP TYPE IF EXISTS video_job_status")
