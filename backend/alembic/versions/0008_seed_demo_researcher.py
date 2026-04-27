"""Seed non-admin demo researcher account

Revision ID: 0008_seed_demo_researcher
Revises: 0007_user_abilities
Create Date: 2026-04-27

Adds a non-admin demo account so the User Abilities matrix has at least one
row with clickable checkboxes (admin rows always show '—').
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from passlib.context import CryptContext

from alembic import op

revision: str = "0008_seed_demo_researcher"
down_revision: str | Sequence[str] | None = "0007_user_abilities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEMO_PASSWORD = "demo123"
RESEARCHER_EMAIL = "researcher"


def upgrade() -> None:
    bind = op.get_bind()
    existing = bind.execute(
        sa.text("SELECT 1 FROM users WHERE email = :email"),
        {"email": RESEARCHER_EMAIL},
    ).first()
    if existing:
        return
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    users = sa.table(
        "users",
        sa.column("id", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.column("email", sa.String),
        sa.column("password_hash", sa.String),
        sa.column("full_name", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("is_admin", sa.Boolean),
    )
    bind.execute(
        users.insert().values(
            id=uuid.uuid4(),
            email=RESEARCHER_EMAIL,
            password_hash=pwd.hash(DEMO_PASSWORD),
            full_name="Sam Researcher",
            is_active=True,
            is_admin=False,
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM users WHERE email = :email"),
        {"email": RESEARCHER_EMAIL},
    )
