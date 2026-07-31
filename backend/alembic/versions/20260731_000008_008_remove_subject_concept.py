"""Remove the "subject" concept entirely from the schema

Revision ID: 008
Revises: 007
Create Date: 2026-07-31

Scoratis dropped subject-based channels/personas in favor of a single
unified tutoring experience. This drops every subject-related column and
the subject_progress table (the old per-subject progress tracker, which
has no unified replacement - the whole feature was removed).

Every index drop uses raw `DROP INDEX IF EXISTS` rather than
`op.drop_index()`: some of these indexes (e.g. idx_conversations_user_subject,
idx_documents_user_subject_status) were declared on the SQLAlchemy models via
Index(...)/index=True but never actually created by a migration on every
environment - only via create_all() fallback during early development - so
their presence is inconsistent across databases. IF EXISTS makes this
migration safe regardless of which indexes a given database actually has.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- conversations ---
    op.execute('DROP INDEX IF EXISTS idx_conversations_user_subject')
    op.execute('DROP INDEX IF EXISTS ix_conversations_subject')
    op.drop_column('conversations', 'subject')

    # --- documents ---
    op.execute('DROP INDEX IF EXISTS idx_documents_user_subject_status')
    op.execute('DROP INDEX IF EXISTS ix_documents_subject')
    op.drop_column('documents', 'subject')

    # --- quizzes ---
    op.execute('DROP INDEX IF EXISTS ix_quizzes_subject')
    op.drop_column('quizzes', 'subject')

    # --- review_items ---
    op.execute('DROP INDEX IF EXISTS ix_review_items_subject')
    op.drop_column('review_items', 'subject')

    # --- subject_progress: entire table (feature removed) ---
    op.execute('DROP INDEX IF EXISTS ix_subject_progress_subject')
    op.execute('DROP INDEX IF EXISTS ix_subject_progress_user_id')
    op.execute('DROP INDEX IF EXISTS ix_subject_progress_id')
    op.drop_table('subject_progress')


def downgrade() -> None:
    # --- subject_progress ---
    op.create_table(
        'subject_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(100), nullable=False),
        sa.Column('total_turns', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_discoveries', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('quizzes_taken', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('quizzes_passed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_interaction_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_subject_progress_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_subject_progress'),
        sa.UniqueConstraint('user_id', 'subject', name='uq_subject_progress_user_subject'),
    )
    op.create_index('ix_subject_progress_id', 'subject_progress', ['id'])
    op.create_index('ix_subject_progress_user_id', 'subject_progress', ['user_id'])
    op.create_index('ix_subject_progress_subject', 'subject_progress', ['subject'])

    # --- review_items ---
    op.add_column('review_items', sa.Column('subject', sa.String(100), nullable=False, server_default='general'))
    op.create_index('ix_review_items_subject', 'review_items', ['subject'])

    # --- quizzes ---
    op.add_column('quizzes', sa.Column('subject', sa.String(100), nullable=False, server_default='general'))
    op.create_index('ix_quizzes_subject', 'quizzes', ['subject'])

    # --- documents ---
    op.add_column('documents', sa.Column('subject', sa.String(100), nullable=True))
    op.create_index('ix_documents_subject', 'documents', ['subject'])

    # --- conversations ---
    op.add_column('conversations', sa.Column('subject', sa.String(100), nullable=True, server_default='general'))
