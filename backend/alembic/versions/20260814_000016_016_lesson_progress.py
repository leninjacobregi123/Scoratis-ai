"""Track learner progress through a lesson

Revision ID: 016
Revises: 015
Create Date: 2026-08-14

Adds per-learner progress to `lessons`. Deliberately separate from
`progress_percent`, which tracks GENERATION (0-100 while the Celery task
builds the lesson) and would be meaningless to overload with "how far the
student got".

`completed_scene_ids` is a JSONB array of scene ids rather than a count, so
scenes completed out of order are recorded accurately and the UI can tick
individual scenes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '016'
down_revision: Union[str, None] = '015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'lessons',
        sa.Column('completed_scene_ids', postgresql.JSONB(), nullable=True,
                  server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column(
        'lessons',
        sa.Column('last_scene_index', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('lessons', 'last_scene_index')
    op.drop_column('lessons', 'completed_scene_ids')
