"""Add first_name/last_name to users; seed manage_users ability; grant to admins

Revision ID: 0009
Revises: 0008_seed_demo_researcher
Create Date: 2026-05-02
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008_seed_demo_researcher"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Add first_name & last_name to users ---
    op.add_column("users", sa.Column("first_name", sa.String(128), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(128), nullable=True))

    # --- Seed manage_users ability ---
    op.execute(
        sa.text(
            "INSERT INTO abilities (key, description) VALUES "
            "('manage_users', 'Create and delete user accounts')"
        )
    )

    # --- Grant manage_users to existing admins ---
    op.execute(
        sa.text(
            "INSERT INTO user_abilities (user_id, ability_key) "
            "SELECT id, 'manage_users' FROM users WHERE is_admin = TRUE"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM user_abilities WHERE ability_key = 'manage_users'")
    )
    op.execute(sa.text("DELETE FROM abilities WHERE key = 'manage_users'"))
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
