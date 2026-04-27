"""Add is_admin to users; create abilities and user_abilities tables; seed demo admins

Revision ID: 0007_user_abilities
Revises: e4144dcdb2c8
Create Date: 2026-04-26
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "0007_user_abilities"
down_revision = "e4144dcdb2c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- is_admin on users ---
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), server_default="false", nullable=False),
    )

    # --- abilities lookup table ---
    op.create_table(
        "abilities",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("description", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # --- user_abilities join table ---
    op.create_table(
        "user_abilities",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("ability_key", sa.String(128), sa.ForeignKey("abilities.key", ondelete="CASCADE"), primary_key=True),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # --- Seed: promote demo users to admin ---
    op.execute(
        sa.text("UPDATE users SET is_admin = TRUE WHERE email IN ('david', 'nate', 'jun')")
    )

    # --- Seed: first example ability definition ---
    op.execute(
        sa.text(
            "INSERT INTO abilities (key, description) VALUES "
            "('manage_ingredients', 'Create, update, and delete global ingredients')"
        )
    )


def downgrade() -> None:
    op.drop_table("user_abilities")
    op.drop_table("abilities")
    op.drop_column("users", "is_admin")
