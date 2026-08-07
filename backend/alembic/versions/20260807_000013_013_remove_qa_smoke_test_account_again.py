"""Remove qa_smoke_test account (second pass)

Revision ID: 013
Revises: 012
Create Date: 2026-08-07

Migration 012 deleted the original qa_smoke_test account. Verifying that
deletion actually worked (by re-signing-up with the same username/email
to confirm the unique constraint no longer blocked it) created a second,
equally disposable account under the same username. Same cleanup, same
reasoning as 012 - see that migration's docstring.
"""
from typing import Sequence, Union

from alembic import op

revision: str = '013'
down_revision: Union[str, None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "DELETE FROM users WHERE username = 'qa_smoke_test' "
        "AND email = 'qa-smoke-test@example.com'"
    )


def downgrade() -> None:
    pass
