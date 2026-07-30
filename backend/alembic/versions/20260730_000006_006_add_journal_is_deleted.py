"""Add journals.is_deleted (soft-delete flag already used by the model/ORM)

Revision ID: 006
Revises: 005
Create Date: 2026-07-30

models/journal.py's Journal.is_deleted has existed for a while but was never
captured in a migration - it was only surfaced because SQLAlchemy's
create_all() (run alongside Alembic at app startup) creates missing tables
but never alters existing ones, so any dev DB that already had a `journals`
table from an earlier migration silently kept working without this column
ever actually existing anywhere except in-memory on the model. A genuinely
fresh DB (e.g. a new deploy) hits it immediately: get_user_stats()'s
`WHERE journals.is_deleted = false` 500s with UndefinedColumnError.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('journals', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('journals', 'is_deleted')
