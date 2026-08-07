"""Remove disposable QA smoke-test account

Revision ID: 012
Revises: 011
Create Date: 2026-08-07

One-off data cleanup, not a schema change: a disposable account
(username='qa_smoke_test') was created directly against production via the
public signup endpoint to verify auth/journals/documents/quizzes/sharing
end-to-end after a deploy. Its journal, document, and conversation were
already removed through the normal API - this just removes the account
row itself, since there's no self-service account-deletion endpoint.
Every user_id foreign key in this schema is ON DELETE CASCADE (see
models/*.py), so this is safe even if anything was missed.

Scoped tightly by exact username so this is a no-op everywhere else
(local dev, other environments) where that account never existed.
"""
from typing import Sequence, Union

from alembic import op

revision: str = '012'
down_revision: Union[str, None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "DELETE FROM users WHERE username = 'qa_smoke_test' "
        "AND email = 'qa-smoke-test@example.com'"
    )


def downgrade() -> None:
    # Data deletion isn't reversible - nothing to restore.
    pass
