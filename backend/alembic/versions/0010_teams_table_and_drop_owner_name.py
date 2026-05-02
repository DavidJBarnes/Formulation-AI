"""Create teams table; replace project.team VARCHAR with team_id FK; drop owner_name

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-02
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create teams table
    op.create_table(
        "teams",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(128), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 2. Migrate existing team names into teams table
    op.execute(
        sa.text(
            "INSERT INTO teams (name) "
            "SELECT DISTINCT team FROM projects WHERE team IS NOT NULL AND team != '' "
            "ON CONFLICT (name) DO NOTHING"
        )
    )

    # 3. Add team_id column (nullable initially)
    op.add_column("projects", sa.Column("team_id", UUID(as_uuid=True), nullable=True))

    # 4. Update project.team_id to match the corresponding team
    op.execute(
        sa.text(
            "UPDATE projects SET team_id = (SELECT id FROM teams WHERE teams.name = projects.team)"
        )
    )

    # 5. Add FK constraint on team_id
    op.create_foreign_key(
        "fk_projects_team_id", "projects", "teams", ["team_id"], ["id"], ondelete="SET NULL"
    )

    # 6. Drop the old team column
    op.drop_column("projects", "team")

    # 7. Drop owner_name column (derived from user join now)
    op.drop_column("projects", "owner_name")


def downgrade() -> None:
    op.add_column("projects", sa.Column("owner_name", sa.String(256), nullable=True))
    op.add_column("projects", sa.Column("team", sa.String(128), nullable=True))

    op.execute(
        sa.text(
            "UPDATE projects SET team = (SELECT name FROM teams WHERE teams.id = projects.team_id)"
        )
    )
    # Restore owner_name from users join
    op.execute(
        sa.text(
            "UPDATE projects SET owner_name = (SELECT full_name FROM users WHERE users.id = projects.owner_id)"
        )
    )

    op.drop_constraint("fk_projects_team_id", "projects", type_="foreignkey")
    op.drop_column("projects", "team_id")
    op.drop_table("teams")
