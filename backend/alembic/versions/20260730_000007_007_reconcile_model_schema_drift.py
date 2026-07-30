"""Reconcile schema drift between models and migrations (users, documents,
chat_messages, learning_states, llm_provider_configs)

Revision ID: 007
Revises: 006
Create Date: 2026-07-30

These tables' SQLAlchemy models had drifted from what the migrations
actually created - a genuinely fresh DB (no ad-hoc manual patches a long-
running dev DB might have accumulated) hits UndefinedColumnError the moment
a code path touches the missing columns, exactly like journals.is_deleted
in migration 006. Found by diffing `models.Base.metadata` against the live
information_schema on a brand-new deploy.

users/documents: additive only (nullable columns the model expects but the
initial migration never added).

chat_messages: migration 001 named the message-text column `content`, the
model calls it `message` - a genuine rename, not a new field. `metadata`
was never adopted by the model - dropped as dead weight.

learning_states: substantially redesigned at the model layer (from a single
opaque `state_data` JSONB blob to named columns matching
ConversationAnalyzer's actual state fields) without ever getting a
migration. Old subject/state_data/misconceptions columns are replaced.

llm_provider_configs: the biggest drift - `model_id` (NOT NULL) vs the
model's `name`, `config` vs `extra_settings`, missing `is_default`, and the
Postgres enum itself both has the wrong values (missing lmstudio/localai/
textgenwebui/azure, has since-removed mistral/cohere/openrouter/xai) AND
the wrong type name (`providertype` vs the model's `provider_type`).
Postgres can't rename/narrow an enum's values in place without dropping and
recreating it, so - since this table has zero rows on every environment
this has been checked against - the table and its enum are dropped and
recreated to match the model exactly, rather than piecing together a
fragile ALTER TYPE sequence for no benefit over a clean rebuild.

If this is ever run against a database that already has real rows in
llm_provider_configs, back up that table first - this migration does not
attempt to preserve or migrate its data.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users: additive ---
    op.add_column('users', sa.Column('preferences', sa.Text(), nullable=True))

    # --- documents: additive ---
    op.add_column('documents', sa.Column('subject', sa.String(100), nullable=True))
    op.create_index('ix_documents_subject', 'documents', ['subject'])

    # --- chat_messages: rename + drop unused ---
    op.alter_column('chat_messages', 'content', new_column_name='message')
    op.drop_column('chat_messages', 'metadata')

    # --- learning_states: replace stale columns with what the model uses ---
    op.drop_column('learning_states', 'subject')
    op.drop_column('learning_states', 'state_data')
    op.drop_column('learning_states', 'misconceptions')
    op.add_column('learning_states', sa.Column('topic', sa.String(500), nullable=True))
    op.add_column('learning_states', sa.Column('turn_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('learning_states', sa.Column('confusion_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('learning_states', sa.Column('understanding_signals', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('learning_states', sa.Column('last_state', sa.String(50), nullable=False, server_default='initial'))
    op.add_column('learning_states', sa.Column('content_richness', sa.String(50), nullable=False, server_default='empty'))
    op.add_column('learning_states', sa.Column('content_score', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('learning_states', sa.Column('extracted_concepts', postgresql.JSONB(), nullable=True))
    op.add_column('learning_states', sa.Column('conversation_context', postgresql.JSONB(), nullable=True))

    # --- llm_provider_configs: drop and recreate to match the model exactly ---
    op.drop_index('ix_llm_provider_configs_user_provider', table_name='llm_provider_configs')
    op.drop_index('ix_llm_provider_configs_id', table_name='llm_provider_configs')
    op.drop_table('llm_provider_configs')
    op.execute("DROP TYPE IF EXISTS providertype")
    # The app's own SQLAlchemy create_all() (run alongside Alembic at every
    # startup - see migration 006's docstring) may have already speculatively
    # created a type named exactly `provider_type` on a prior boot, from the
    # model's `name="provider_type"` before this migration ever ran. Drop it
    # too so op.create_table's own creation below doesn't hit DuplicateObject.
    op.execute("DROP TYPE IF EXISTS provider_type")

    # Not pre-created separately - op.create_table's inline enum column
    # below auto-creates the type as part of the table DDL (the standard
    # Alembic pattern); calling .create() here too would double-create it.
    provider_type_enum = postgresql.ENUM(
        'ollama', 'lmstudio', 'localai', 'textgenwebui',
        'openai', 'anthropic', 'google', 'groq', 'together', 'azure', 'deepseek',
        name='provider_type',
    )

    op.create_table(
        'llm_provider_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', provider_type_enum, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('api_key_encrypted', sa.Text(), nullable=True),
        sa.Column('base_url', sa.String(500), nullable=True),
        sa.Column('extra_settings', postgresql.JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_llm_provider_configs_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_llm_provider_configs'),
    )
    op.create_index('ix_llm_provider_configs_id', 'llm_provider_configs', ['id'])
    op.create_index('ix_llm_provider_configs_user_provider', 'llm_provider_configs', ['user_id', 'provider'])


def downgrade() -> None:
    op.drop_index('ix_llm_provider_configs_user_provider', table_name='llm_provider_configs')
    op.drop_index('ix_llm_provider_configs_id', table_name='llm_provider_configs')
    op.drop_table('llm_provider_configs')
    op.execute("DROP TYPE IF EXISTS provider_type")

    old_provider_type_enum = postgresql.ENUM(
        'openai', 'anthropic', 'google', 'ollama', 'groq', 'mistral', 'cohere',
        'together', 'openrouter', 'deepseek', 'xai',
        name='providertype',
    )
    op.create_table(
        'llm_provider_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', old_provider_type_enum, nullable=False),
        sa.Column('api_key_encrypted', sa.Text(), nullable=True),
        sa.Column('model_id', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('base_url', sa.String(500), nullable=True),
        sa.Column('config', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_llm_provider_configs_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_llm_provider_configs'),
    )
    op.create_index('ix_llm_provider_configs_id', 'llm_provider_configs', ['id'])
    op.create_index('ix_llm_provider_configs_user_provider', 'llm_provider_configs', ['user_id', 'provider'])

    op.add_column('learning_states', sa.Column('misconceptions', postgresql.JSONB(), nullable=True))
    op.add_column('learning_states', sa.Column('state_data', postgresql.JSONB(), nullable=True))
    op.add_column('learning_states', sa.Column('subject', sa.String(100), nullable=True))
    op.drop_column('learning_states', 'conversation_context')
    op.drop_column('learning_states', 'extracted_concepts')
    op.drop_column('learning_states', 'content_score')
    op.drop_column('learning_states', 'content_richness')
    op.drop_column('learning_states', 'last_state')
    op.drop_column('learning_states', 'understanding_signals')
    op.drop_column('learning_states', 'confusion_count')
    op.drop_column('learning_states', 'turn_count')
    op.drop_column('learning_states', 'topic')

    op.add_column('chat_messages', sa.Column('metadata', postgresql.JSONB(), nullable=True))
    op.alter_column('chat_messages', 'message', new_column_name='content')

    op.drop_index('ix_documents_subject', table_name='documents')
    op.drop_column('documents', 'subject')

    op.drop_column('users', 'preferences')
