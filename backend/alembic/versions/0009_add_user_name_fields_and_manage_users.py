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
    # --- Add first_name & last_name to users (idempotent) ---
    _add_column_if_not_exists("users", "first_name", sa.String(128))
    _add_column_if_not_exists("users", "last_name", sa.String(128))

    # --- Seed manage_users ability (idempotent) ---
    op.execute(
        sa.text(
            "INSERT INTO abilities (key, description) VALUES "
            "('manage_users', 'Create and delete user accounts') "
            "ON CONFLICT (key) DO NOTHING"
        )
    )

    # --- Grant manage_users to existing admins (idempotent) ---
    op.execute(
        sa.text(
            "INSERT INTO user_abilities (user_id, ability_key) "
            "SELECT id, 'manage_users' FROM users WHERE is_admin = TRUE "
            "ON CONFLICT (user_id, ability_key) DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM user_abilities WHERE ability_key = 'manage_users'")
    )
    op.execute(sa.text("DELETE FROM abilities WHERE key = 'manage_users'"))
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")


def _add_column_if_not_exists(table: str, column: str, col_type) -> None:
    """Add a column only if it doesn't already exist (for retry resilience)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :col"
        ),
        {"table": table, "col": column},
    ).first()
    if not result:
        op.add_column(table, sa.Column(column, col_type, nullable=True))
