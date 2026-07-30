"""Add authentication fields to users

Revision ID: 002
Revises: 001
Create Date: 2026-07-23

Adds hashed_password/is_active to users and makes email required+unique.
Backfills the legacy single seeded user (id=1, created by database.py's
init routine as username="Lenin") with a real email + a placeholder
password hash so the row keeps satisfying the new NOT NULL constraints.
That placeholder is not a usable password - it forces a password reset
on first login rather than leaving a guessable default credential.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# bcrypt hash of a random, never-communicated placeholder - unusable as a
# login credential. Real accounts get real hashes via /auth/signup.
_PLACEHOLDER_HASH = "$2b$12$CwTycUXWue0Thq9StjUM0uJ8i7EN6NakiRRPUpY9x/HDXCLKt7VLK"


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('hashed_password', sa.String(length=255), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # Backfill any existing rows (the legacy single-user seed) before
    # tightening constraints, so the migration works on both a fresh DB
    # and an existing dev database that already has a users row.
    op.execute(f"""
        UPDATE users
        SET hashed_password = '{_PLACEHOLDER_HASH}'
        WHERE hashed_password IS NULL
    """)
    op.execute("""
        UPDATE users
        SET email = 'user' || id || '@scoratis.local'
        WHERE email IS NULL
    """)

    op.alter_column('users', 'hashed_password', nullable=False)
    op.alter_column('users', 'email', nullable=False)

    # Some dev databases were bootstrapped via SQLAlchemy's create_all() (the
    # "auto" MIGRATION_MODE) rather than Alembic, and the User model already
    # declared email as unique=True - so the constraint may already exist.
    # Guard against that instead of failing the whole migration.
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE users ADD CONSTRAINT uq_users_email UNIQUE (email);
        EXCEPTION
            WHEN duplicate_table THEN null;
        END $$;
    """)

    # database.py used to auto-seed a "default user" with a hardcoded id=1
    # on every startup (a legacy single-user-era pattern, now removed since
    # real signup exists). That INSERT with an explicit PK bypassed
    # users_id_seq, so the sequence is still at its start value on any
    # database that has that row - the first real signup would then collide
    # on id=1. Bring the sequence back in sync with the actual max id.
    op.execute("""
        SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 1))
    """)


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE users DROP CONSTRAINT uq_users_email;
        EXCEPTION
            WHEN undefined_object THEN null;
        END $$;
    """)
    op.alter_column('users', 'email', nullable=True)
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'hashed_password')
