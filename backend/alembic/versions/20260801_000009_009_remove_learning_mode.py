"""Remove the exam_prep/deep_learning "learning mode" concept

Revision ID: 009
Revises: 008
Create Date: 2026-08-01

Scoratis is dropping the Exam Prep / Deep Learning mode picker entirely in
favor of a single, unified Socratic tutoring experience - mirrors migration
008's removal of the "subject" concept. Drops conversations.learning_mode
and conversations.mode_context, added by migration 005.

Uses raw `DROP INDEX IF EXISTS` rather than `op.drop_index()` for the same
reason migration 008 does: these columns were never actually indexed by a
migration, but IF EXISTS keeps this safe regardless of dev-DB drift.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('DROP INDEX IF EXISTS ix_conversations_learning_mode')
    op.drop_column('conversations', 'mode_context')
    op.drop_column('conversations', 'learning_mode')


def downgrade() -> None:
    op.add_column('conversations', sa.Column('learning_mode', sa.String(20), nullable=True))
    op.add_column('conversations', sa.Column('mode_context', sa.String(500), nullable=True))
