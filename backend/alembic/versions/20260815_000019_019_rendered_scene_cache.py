"""Cache rendered animations so the same idea is not re-rendered

Revision ID: 019
Revises: 018
Create Date: 2026-08-15

A Manim render costs roughly a minute of CPU plus several model calls, and
was paid again every time a lesson happened to cover ground an earlier one
already animated. This table makes a finished render findable by what it
teaches.

source_lesson_id is SET NULL rather than CASCADE: deleting the lesson that
happened to produce a render should not throw away a file every later lesson
could still use.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision: str = '019'
down_revision: Union[str, None] = '018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'rendered_scenes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('slug', sa.String(length=300), nullable=False),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('video_path', sa.String(length=500), nullable=False),
        sa.Column('poster_path', sa.String(length=500), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('source_lesson_id', sa.Integer(), nullable=True),
        sa.Column('use_count', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_lesson_id'], ['lessons.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_rendered_scenes_id', 'rendered_scenes', ['id'])
    op.create_index('ix_rendered_scenes_user_id', 'rendered_scenes', ['user_id'])
    op.create_index('ix_rendered_scenes_slug', 'rendered_scenes', ['slug'])
    op.create_index('ix_rendered_scenes_user_slug', 'rendered_scenes', ['user_id', 'slug'])


def downgrade() -> None:
    op.drop_index('ix_rendered_scenes_user_slug', table_name='rendered_scenes')
    op.drop_index('ix_rendered_scenes_slug', table_name='rendered_scenes')
    op.drop_index('ix_rendered_scenes_user_id', table_name='rendered_scenes')
    op.drop_index('ix_rendered_scenes_id', table_name='rendered_scenes')
    op.drop_table('rendered_scenes')
