"""phase2_hardening_context_columns

Add context_json to cases table and india_context_json to assessments table.

context_json: Stores structured intake form data (incident type, location,
              safety status, identity context). Nullable for backward compat.
              Identity fields are never exposed to the LLM.

india_context_json: Stores deterministic India legal/contextual relevance
                    assessment output from IndiaContextLayer. Nullable for
                    backward compat with existing assessment records.

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-09-23 22:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("cases", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "context_json",
                sa.JSON(),
                nullable=True,
                comment=(
                    "Structured intake context. Never contains complaint text. "
                    "Identity fields not exposed to LLM."
                ),
            )
        )

    with op.batch_alter_table("assessments", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "india_context_json",
                sa.JSON(),
                nullable=True,
                comment=(
                    "Deterministic India legal/contextual relevance assessment. "
                    "Advisory only — not a legal determination."
                ),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("assessments", schema=None) as batch_op:
        batch_op.drop_column("india_context_json")

    with op.batch_alter_table("cases", schema=None) as batch_op:
        batch_op.drop_column("context_json")
