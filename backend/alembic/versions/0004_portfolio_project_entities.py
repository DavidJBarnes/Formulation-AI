"""portfolio and project entities

Revision ID: 0004_portfolio_project_entities
Revises: 0003_fix_demo_user_logins
Create Date: 2026-04-26

Full normalized schema for the Portfolio → Project → Iteration → Formulation
hierarchy, plus global ingredient and output-property registries.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_portfolio_project_entities"
down_revision: str | Sequence[str] | None = "0003_fix_demo_user_logins"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # portfolios
    # ------------------------------------------------------------------
    op.create_table(
        "portfolios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("row_created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("row_updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ------------------------------------------------------------------
    # projects
    # ------------------------------------------------------------------
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("domain", sa.String(128), nullable=True),
        sa.Column("team", sa.String(128), nullable=True),
        sa.Column("status", sa.String(16), server_default="planning", nullable=False),
        sa.Column("started_at", sa.Date, nullable=True),
        sa.Column("ends_at", sa.Date, nullable=True),
        sa.Column("max_iterations", sa.Integer, server_default="6", nullable=False),
        sa.Column("flag_note", sa.Text, nullable=True),
        sa.Column("row_created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("row_updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_projects_portfolio_id", "projects", ["portfolio_id"])

    # ------------------------------------------------------------------
    # global ingredient registry
    # ------------------------------------------------------------------
    op.create_table(
        "ingredients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False, unique=True),
        sa.Column("default_unit", sa.String(32), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ingredients_name", "ingredients", ["name"], unique=True)

    # ------------------------------------------------------------------
    # project-scoped ingredient spec (bounds for optimizer)
    # ------------------------------------------------------------------
    op.create_table(
        "project_ingredients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ingredients.id"), nullable=False),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.Column("min_amount", sa.Float, nullable=True),
        sa.Column("max_amount", sa.Float, nullable=True),
        sa.Column("sort_order", sa.Integer, server_default="0", nullable=False),
        sa.UniqueConstraint("project_id", "ingredient_id", name="uq_project_ingredient"),
    )
    op.create_index("ix_project_ingredients_project_id", "project_ingredients", ["project_id"])

    # ------------------------------------------------------------------
    # global output-property registry
    # ------------------------------------------------------------------
    op.create_table(
        "output_properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False, unique=True),
        sa.Column("default_unit", sa.String(32), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_output_properties_name", "output_properties", ["name"], unique=True)

    # ------------------------------------------------------------------
    # project targets
    # ------------------------------------------------------------------
    op.create_table(
        "project_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("output_property_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("output_properties.id"), nullable=False),
        sa.Column("goal", sa.String(64), nullable=False),
        sa.Column("reference_label", sa.String(256), nullable=True),
        sa.Column("sort_order", sa.Integer, server_default="0", nullable=False),
    )
    op.create_index("ix_project_targets_project_id", "project_targets", ["project_id"])

    # ------------------------------------------------------------------
    # iterations
    # ------------------------------------------------------------------
    op.create_table(
        "iterations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("n", sa.Integer, nullable=False),
        sa.Column("status", sa.String(16), server_default="queued", nullable=False),
        sa.Column("best_objective", sa.Float, nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_iterations_project_id", "iterations", ["project_id"])

    # ------------------------------------------------------------------
    # formulations
    # ------------------------------------------------------------------
    op.create_table(
        "formulations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("iteration_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("iterations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("label", sa.String(128), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column("flagged", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_formulations_project_id", "formulations", ["project_id"])
    op.create_index("ix_formulations_iteration_id", "formulations", ["iteration_id"])

    # ------------------------------------------------------------------
    # formulation ingredients (amounts per recipe)
    # ------------------------------------------------------------------
    op.create_table(
        "formulation_ingredients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("formulation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("formulations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_ingredient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project_ingredients.id"), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
    )
    op.create_index("ix_formulation_ingredients_formulation_id", "formulation_ingredients", ["formulation_id"])

    # ------------------------------------------------------------------
    # formulation properties (measured or predicted values)
    # ------------------------------------------------------------------
    op.create_table(
        "formulation_properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("formulation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("formulations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_target_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project_targets.id"), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("sigma", sa.Float, nullable=True),
    )
    op.create_index("ix_formulation_properties_formulation_id", "formulation_properties", ["formulation_id"])


def downgrade() -> None:
    op.drop_table("formulation_properties")
    op.drop_table("formulation_ingredients")
    op.drop_table("formulations")
    op.drop_table("iterations")
    op.drop_table("project_targets")
    op.drop_table("output_properties")
    op.drop_table("project_ingredients")
    op.drop_table("ingredients")
    op.drop_table("projects")
    op.drop_table("portfolios")
