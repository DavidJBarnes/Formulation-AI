"""add_optimizer_columns

Revision ID: fa3cabb616cf
Revises: ba932e929341
Create Date: 2026-04-26 13:20:19.860332

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = 'fa3cabb616cf'
down_revision: str | Sequence[str] | None = 'ba932e929341'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
