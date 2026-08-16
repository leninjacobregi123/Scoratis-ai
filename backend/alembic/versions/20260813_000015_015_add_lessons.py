"""Add lessons table for MAIC-style interactive lesson generation

Revision ID: 015
Revises: 014
Create Date: 2026-08-13

Backs models/lesson.py. Scenes and outline are JSONB rather than child tables:
a lesson is always read whole by the player, never queried scene-by-scene, and
the scene shape is a contract owned by the frontend renderer (@maic/dsl) that
would otherwise force a migration every time the DSL evolves.

The status enum is created with explicit lowercase labels to match
SQLEnum(values_callable=...) on the model - same pattern as video_job_status
and provider_type; without it every insert fails with
InvalidTextRepresentationError.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '015'
down_revision: Union[str, None] = '014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Guarded so a database that already ran an earlier hand-applied version
    # of this migration doesn't fail on re-run (same defensive style as 014).
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE lesson_status AS ENUM ('pending', 'generating', 'completed', 'failed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.create_table(
        'lessons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('requirement', sa.Text(), nullable=False),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column(
            'status',
            postgresql.ENUM('pending', 'generating', 'completed', 'failed',
                            name='lesson_status', create_type=False),
            nullable=False,
            server_default='pending',
        ),
        sa.Column('stage', sa.String(50), nullable=True),
        sa.Column('progress_percent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('message', sa.String(500), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('outline', postgresql.JSONB(), nullable=True),
        sa.Column('scenes', postgresql.JSONB(), nullable=True),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_lessons_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_lessons'),
    )
    op.create_index('ix_lessons_id', 'lessons', ['id'])
    op.create_index('ix_lessons_user_id', 'lessons', ['user_id'])
    op.create_index('ix_lessons_status', 'lessons', ['status'])
    op.create_index('ix_lessons_session_id', 'lessons', ['session_id'])


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS ix_lessons_session_id')
    op.execute('DROP INDEX IF EXISTS ix_lessons_status')
    op.execute('DROP INDEX IF EXISTS ix_lessons_user_id')
    op.execute('DROP INDEX IF EXISTS ix_lessons_id')
    op.execute('DROP TABLE IF EXISTS lessons')
    op.execute('DROP TYPE IF EXISTS lesson_status')
