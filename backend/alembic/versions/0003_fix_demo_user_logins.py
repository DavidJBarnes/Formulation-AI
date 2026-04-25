"""fix demo user logins to bare usernames

Revision ID: 0003_fix_demo_user_logins
Revises: 0002_seed_demo_users
Create Date: 2026-04-25

Replaces the made-up email addresses from 0002 with the bare usernames
the team actually uses to sign in: david, nate, jun (still password demo123).
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from passlib.context import CryptContext

from alembic import op

revision: str = "0003_fix_demo_user_logins"
down_revision: str | Sequence[str] | None = "0002_seed_demo_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEMO_PASSWORD = "demo123"

WRONG_EMAILS = [
    "david.barnes@employbridge.com",
    "nate@formulationai.dev",
    "jun.liu@revvity.com",
]

DEMO_USERS = [
    {"email": "david", "full_name": "David Barnes"},
    {"email": "nate", "full_name": "Nate"},
    {"email": "jun", "full_name": "Jun Liu"},
]


def upgrade() -> None:
    bind = op.get_bind()

    # Remove the made-up emails from 0002 if still present.
    bind.execute(
        sa.text("DELETE FROM users WHERE email = ANY(:emails)"),
        {"emails": WRONG_EMAILS},
    )

    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
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
    bind.execute(
        sa.text("DELETE FROM users WHERE email = ANY(:emails)"),
        {"emails": [u["email"] for u in DEMO_USERS]},
    )
