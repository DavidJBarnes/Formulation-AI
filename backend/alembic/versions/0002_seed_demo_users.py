"""seed demo users

Revision ID: 0002_seed_demo_users
Revises: 0001_users
Create Date: 2026-04-24

Idempotent seed of three demo accounts (david/nate/jun) with password "demo123".
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from passlib.context import CryptContext

from alembic import op

revision: str = "0002_seed_demo_users"
down_revision: str | Sequence[str] | None = "0001_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEMO_PASSWORD = "demo123"

DEMO_USERS = [
    {"email": "david.barnes@employbridge.com", "full_name": "David Barnes"},
    {"email": "nate@formulationai.dev", "full_name": "Nate"},
    {"email": "jun.liu@revvity.com", "full_name": "Jun Liu"},
]


def upgrade() -> None:
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    bind = op.get_bind()
    users = sa.table(
        "users",
        sa.column("id", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.column("email", sa.String),
        sa.column("password_hash", sa.String),
        sa.column("full_name", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    for u in DEMO_USERS:
        existing = bind.execute(
            sa.text("SELECT 1 FROM users WHERE email = :email"),
            {"email": u["email"]},
        ).first()
        if existing:
            continue
        bind.execute(
            users.insert().values(
                id=uuid.uuid4(),
                email=u["email"],
                password_hash=pwd.hash(DEMO_PASSWORD),
                full_name=u["full_name"],
                is_active=True,
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    for u in DEMO_USERS:
        bind.execute(
            sa.text("DELETE FROM users WHERE email = :email"),
            {"email": u["email"]},
        )
