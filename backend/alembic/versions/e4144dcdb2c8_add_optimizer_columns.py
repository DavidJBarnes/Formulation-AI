"""add_optimizer_columns

Revision ID: e4144dcdb2c8
Revises: fa3cabb616cf
Create Date: 2026-04-26 13:26:58.740778

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = 'e4144dcdb2c8'
down_revision: str | Sequence[str] | None = 'fa3cabb616cf'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
