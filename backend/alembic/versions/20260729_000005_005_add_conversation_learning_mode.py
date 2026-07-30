"""Add conversation learning_mode (exam_prep vs deep_learning intent capture)

Revision ID: 005
Revises: 004
Create Date: 2026-07-29

Students either want fast, direct answers for an upcoming exam, or full
Socratic-method deep learning. Captured once per new conversation, stored on
the conversation row, switchable afterward via a header toggle. NULL means
"not yet chosen" - all pre-existing conversations resolve to the unchanged
deep_learning behavior at the application layer, not via a DB default, so
this migration itself has zero effect on existing conversations.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('conversations', sa.Column('learning_mode', sa.String(20), nullable=True))
    op.add_column('conversations', sa.Column('mode_context', sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column('conversations', 'mode_context')
    op.drop_column('conversations', 'learning_mode')
