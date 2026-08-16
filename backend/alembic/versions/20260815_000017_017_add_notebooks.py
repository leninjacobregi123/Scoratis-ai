"""Add notebooks, and file existing work into one

Revision ID: 017
Revises: 016
Create Date: 2026-08-15

Introduces the notebook: a student's container for study, owning their
conversations and the lessons generated from them. Nesting is a
self-referential parent_id; cycle and depth rules live in the API layer,
not in the schema.

The backfill is the part that matters. Conversations and lessons already
exist, unfiled, and the moment the UI starts filtering by notebook an
unfiled row becomes invisible. So every user with existing work gets a
"My Notebook" and all of it is moved in - nothing is stranded, and the
first thing a returning student sees is their own history rather than an
empty shelf.

Both new foreign keys are ON DELETE SET NULL, never CASCADE: a notebook
can hold hours of generated courses, and removing the folder must not
destroy the contents.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '017'
down_revision: Union[str, None] = '016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'notebooks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('last_opened_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        # A removed parent promotes its children to the top level instead
        # of deleting the subtree.
        sa.ForeignKeyConstraint(['parent_id'], ['notebooks.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notebooks_id', 'notebooks', ['id'])
    op.create_index('ix_notebooks_user_id', 'notebooks', ['user_id'])
    op.create_index('ix_notebooks_parent_id', 'notebooks', ['parent_id'])
    op.create_index('ix_notebooks_last_opened_at', 'notebooks', ['last_opened_at'])
    op.create_index('ix_notebooks_user_archived', 'notebooks', ['user_id', 'archived_at'])

    op.add_column('conversations', sa.Column('notebook_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_conversations_notebook_id', 'conversations', 'notebooks',
        ['notebook_id'], ['id'], ondelete='SET NULL',
    )
    op.create_index('ix_conversations_notebook_id', 'conversations', ['notebook_id'])

    op.add_column('lessons', sa.Column('notebook_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_lessons_notebook_id', 'lessons', 'notebooks',
        ['notebook_id'], ['id'], ondelete='SET NULL',
    )
    op.create_index('ix_lessons_notebook_id', 'lessons', ['notebook_id'])

    # --- backfill -------------------------------------------------------
    # One notebook per user who already has something to file. Users with
    # no history are left alone; the app creates their first notebook when
    # they sign in, so this migration does not invent empty shelves.
    op.execute("""
        INSERT INTO notebooks (user_id, parent_id, name, description, last_opened_at)
        SELECT u.id, NULL, 'My Notebook',
               'Your existing chats and courses, filed here automatically.',
               now()
        FROM users u
        WHERE EXISTS (SELECT 1 FROM conversations c WHERE c.user_id = u.id)
           OR EXISTS (SELECT 1 FROM lessons l WHERE l.user_id = u.id)
    """)
    op.execute("""
        UPDATE conversations c
        SET notebook_id = n.id
        FROM notebooks n
        WHERE n.user_id = c.user_id
          AND n.parent_id IS NULL
          AND n.name = 'My Notebook'
          AND c.notebook_id IS NULL
    """)
    op.execute("""
        UPDATE lessons l
        SET notebook_id = n.id
        FROM notebooks n
        WHERE n.user_id = l.user_id
          AND n.parent_id IS NULL
          AND n.name = 'My Notebook'
          AND l.notebook_id IS NULL
    """)


def downgrade() -> None:
    # Dropping the columns unfiles everything, which is exactly the state
    # before this migration ran - no conversation or lesson is lost.
    op.drop_index('ix_lessons_notebook_id', table_name='lessons')
    op.drop_constraint('fk_lessons_notebook_id', 'lessons', type_='foreignkey')
    op.drop_column('lessons', 'notebook_id')

    op.drop_index('ix_conversations_notebook_id', table_name='conversations')
    op.drop_constraint('fk_conversations_notebook_id', 'conversations', type_='foreignkey')
    op.drop_column('conversations', 'notebook_id')

    op.drop_index('ix_notebooks_user_archived', table_name='notebooks')
    op.drop_index('ix_notebooks_last_opened_at', table_name='notebooks')
    op.drop_index('ix_notebooks_parent_id', table_name='notebooks')
    op.drop_index('ix_notebooks_user_id', table_name='notebooks')
    op.drop_index('ix_notebooks_id', table_name='notebooks')
    op.drop_table('notebooks')
