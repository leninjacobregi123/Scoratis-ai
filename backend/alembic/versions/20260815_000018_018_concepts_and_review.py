"""Add the concept layer and spaced-repetition review

Revision ID: 018
Revises: 017
Create Date: 2026-08-15

Two features that only work together. The concept tables give lesson content
an addressable idea behind it; the review tables turn those ideas into
questions on a forgetting-curve schedule.

No backfill. Concepts are extracted during lesson generation, and generating
them for the 15 existing lessons would mean 15 model calls against content
whose scenes were written before tagging existed - better done deliberately
from the API than silently inside a migration that cannot be rolled back
cleanly.

The enum is created explicitly with checkfirst, matching the lesson_status
pattern: SQLAlchemy's Enum(create_type=False) in the model means the type
must already exist, and letting the column definition create it implicitly
breaks the downgrade.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


revision: str = '018'
down_revision: Union[str, None] = '017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


review_kind = postgresql.ENUM(
    'recall', 'mcq', 'problem', name='review_kind', create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    review_kind.create(bind, checkfirst=True)

    # --- concept layer --------------------------------------------------
    op.create_table(
        'concepts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=300), nullable=False),
        sa.Column('slug', sa.String(length=300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'slug', name='uq_concepts_user_slug'),
    )
    op.create_index('ix_concepts_id', 'concepts', ['id'])
    op.create_index('ix_concepts_user_id', 'concepts', ['user_id'])
    op.create_index('ix_concepts_slug', 'concepts', ['slug'])

    op.create_table(
        'concept_edges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('prerequisite_id', sa.Integer(), nullable=False),
        sa.Column('dependent_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['prerequisite_id'], ['concepts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['dependent_id'], ['concepts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('prerequisite_id', 'dependent_id', name='uq_concept_edge'),
    )
    op.create_index('ix_concept_edges_user_id', 'concept_edges', ['user_id'])
    op.create_index('ix_concept_edges_prerequisite_id', 'concept_edges', ['prerequisite_id'])
    op.create_index('ix_concept_edges_dependent_id', 'concept_edges', ['dependent_id'])

    op.create_table(
        'scene_concepts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lesson_id', sa.Integer(), nullable=False),
        sa.Column('scene_id', sa.String(length=100), nullable=False),
        sa.Column('concept_id', sa.Integer(), nullable=False),
        sa.Column('is_primary', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['concept_id'], ['concepts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lesson_id', 'scene_id', 'concept_id', name='uq_scene_concept'),
    )
    op.create_index('ix_scene_concepts_lesson_id', 'scene_concepts', ['lesson_id'])
    op.create_index('ix_scene_concepts_concept_id', 'scene_concepts', ['concept_id'])
    op.create_index('ix_scene_concepts_lesson_scene', 'scene_concepts', ['lesson_id', 'scene_id'])

    op.create_table(
        'concept_mastery',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('concept_id', sa.Integer(), nullable=False),
        sa.Column('strength', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('review_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('lapse_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['concept_id'], ['concepts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'concept_id', name='uq_mastery_user_concept'),
    )
    op.create_index('ix_concept_mastery_user_id', 'concept_mastery', ['user_id'])
    op.create_index('ix_concept_mastery_concept_id', 'concept_mastery', ['concept_id'])

    # --- review ---------------------------------------------------------
    # Every link back to source content is SET NULL: deleting a course must
    # not take weeks of the student's review history with it.
    op.create_table(
        'review_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('lesson_id', sa.Integer(), nullable=True),
        sa.Column('scene_id', sa.String(length=100), nullable=True),
        sa.Column('concept_id', sa.Integer(), nullable=True),
        sa.Column('notebook_id', sa.Integer(), nullable=True),
        sa.Column('kind', review_kind, nullable=False, server_default='recall'),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('rubric', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('retired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['concept_id'], ['concepts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['notebook_id'], ['notebooks.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_review_items_id', 'review_items', ['id'])
    op.create_index('ix_review_items_user_id', 'review_items', ['user_id'])
    op.create_index('ix_review_items_lesson_id', 'review_items', ['lesson_id'])
    op.create_index('ix_review_items_concept_id', 'review_items', ['concept_id'])
    op.create_index('ix_review_items_notebook_id', 'review_items', ['notebook_id'])

    op.create_table(
        'review_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('stability', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('difficulty', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('reps', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('lapses', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('last_grade', sa.Integer(), nullable=True),
        sa.Column('last_reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['item_id'], ['review_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('item_id'),
    )
    op.create_index('ix_review_schedules_item_id', 'review_schedules', ['item_id'])
    op.create_index('ix_review_schedules_user_id', 'review_schedules', ['user_id'])
    op.create_index('ix_review_schedules_due_at', 'review_schedules', ['due_at'])
    op.create_index('ix_review_schedules_user_due', 'review_schedules', ['user_id', 'due_at'])

    op.create_table(
        'review_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('grade', sa.Integer(), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('scheduled_days', sa.Float(), nullable=True),
        sa.Column('elapsed_days', sa.Float(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['item_id'], ['review_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_review_logs_item_id', 'review_logs', ['item_id'])
    op.create_index('ix_review_logs_user_id', 'review_logs', ['user_id'])
    op.create_index('ix_review_logs_reviewed_at', 'review_logs', ['reviewed_at'])


def downgrade() -> None:
    op.drop_table('review_logs')
    op.drop_table('review_schedules')
    op.drop_table('review_items')
    op.drop_table('concept_mastery')
    op.drop_table('scene_concepts')
    op.drop_table('concept_edges')
    op.drop_table('concepts')
    review_kind.drop(op.get_bind(), checkfirst=True)
