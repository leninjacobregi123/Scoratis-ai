"""Fix journals.tags column type drift (varchar[] -> jsonb)

Revision ID: 011
Revises: 010
Create Date: 2026-08-04

The Journal model has declared `tags` as JSONB since it was written, but
migration 001 created the actual column as `character varying[]` (a native
Postgres text array) and nothing ever reconciled the two - migration 007's
schema-drift cleanup covered users/documents/chat_messages/learning_states/
llm_provider_configs but missed this one. Every journal-creation request
crashes with `DatatypeMismatchError: column "tags" is of type character
varying[] but expression is of type jsonb` the moment the endpoint is
actually exercised, since the ORM always binds JSONB per the model.

`USING to_jsonb(tags)` converts existing array values (e.g. {'a','b'} ->
'["a", "b"]'::jsonb) rather than discarding them - this table has real data
on the already-live production deployment.
"""
from typing import Sequence, Union

from alembic import op

revision: str = '011'
down_revision: Union[str, None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE journals ALTER COLUMN tags TYPE JSONB USING to_jsonb(tags)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE journals ALTER COLUMN tags TYPE VARCHAR[] "
        "USING ARRAY(SELECT jsonb_array_elements_text(COALESCE(tags, '[]'::jsonb)))"
    )
