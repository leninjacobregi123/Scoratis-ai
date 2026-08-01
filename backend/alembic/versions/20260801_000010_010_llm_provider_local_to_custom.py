"""Remove local LLM providers, add the Custom/private provider

Revision ID: 010
Revises: 009
Create Date: 2026-08-01

Scoratis is dropping Local LLM support (Ollama/LM Studio/LocalAI/Text Gen
WebUI never actually ran on the deployment VM, so this was a dead UI path
in production) in favor of a single "Custom" OpenAI-compatible provider
slot for private/institutional endpoints (e.g. a university's own LLM
gateway).

Unlike migration 007's full drop-and-recreate of llm_provider_configs (safe
at the time because the table had zero rows anywhere), this table may now
have real user-configured cloud provider rows, so this migration converts
the enum column to text, deletes any rows using a removed local-provider
value, rebuilds the `provider_type` enum with the local values dropped and
`custom` added, then converts the column back - preserving every row that
uses a value still valid in the new enum.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '010'
down_revision: Union[str, None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_VALUES = (
    'ollama', 'lmstudio', 'localai', 'textgenwebui',
    'openai', 'anthropic', 'google', 'groq', 'together', 'azure', 'deepseek',
)
NEW_VALUES = (
    'openai', 'anthropic', 'google', 'groq', 'together', 'azure', 'deepseek', 'custom',
)


def upgrade() -> None:
    op.execute(
        "DELETE FROM llm_provider_configs WHERE provider::text IN "
        "('ollama', 'lmstudio', 'localai', 'textgenwebui')"
    )
    op.alter_column(
        'llm_provider_configs', 'provider',
        type_=sa.String(),
        postgresql_using='provider::text',
    )
    op.execute('DROP TYPE provider_type')
    new_enum = sa.Enum(*NEW_VALUES, name='provider_type')
    new_enum.create(op.get_bind())
    op.alter_column(
        'llm_provider_configs', 'provider',
        type_=new_enum,
        postgresql_using='provider::provider_type',
    )


def downgrade() -> None:
    op.alter_column(
        'llm_provider_configs', 'provider',
        type_=sa.String(),
        postgresql_using='provider::text',
    )
    op.execute("DELETE FROM llm_provider_configs WHERE provider = 'custom'")
    op.execute('DROP TYPE provider_type')
    old_enum = sa.Enum(*OLD_VALUES, name='provider_type')
    old_enum.create(op.get_bind())
    op.alter_column(
        'llm_provider_configs', 'provider',
        type_=old_enum,
        postgresql_using='provider::provider_type',
    )
