"""phase2_assessment_indexes

Add composite index on (case_id, assessed_at) for efficient per-case
assessment lookup and a pipeline_version index for filtering by version.

Revision ID: a1b2c3d4e5f6
Revises: d57b808a2e16
Create Date: 2026-09-23 01:14:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "d57b808a2e16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("assessments", schema=None) as batch_op:
        # Composite index for efficient per-case retrieval ordered by time
        batch_op.create_index(
            "ix_assessments_case_id_assessed_at",
            ["case_id", "assessed_at"],
            unique=False,
        )
        # Index for filtering/reporting by pipeline version
        batch_op.create_index(
            "ix_assessments_pipeline_version",
            ["pipeline_version"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("assessments", schema=None) as batch_op:
        batch_op.drop_index("ix_assessments_pipeline_version")
        batch_op.drop_index("ix_assessments_case_id_assessed_at")
