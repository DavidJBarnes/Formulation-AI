"""Add weight to project_targets, batch_total_g to projects

Revision ID: ba932e929341
Revises: 0006_add_model_used
Create Date: 2026-04-26
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "ba932e929341"
down_revision = "0006_add_model_used"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project_targets",
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
    )
    op.add_column(
        "projects",
        sa.Column("batch_total_g", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("project_targets", "weight")
    op.drop_column("projects", "batch_total_g")
