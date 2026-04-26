from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from formulation_ai.models.base import Base

if TYPE_CHECKING:
    from formulation_ai.models.formulation import Formulation
    from formulation_ai.models.project import Project


class Ingredient(Base):
    """Global registry of ingredients — reusable across projects."""

    __tablename__ = "ingredients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(256), unique=True, nullable=False, index=True)
    default_unit: Mapped[str | None] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project_ingredients: Mapped[list[ProjectIngredient]] = relationship(back_populates="ingredient")


class ProjectIngredient(Base):
    """
    Ingredient spec scoped to a project: which ingredients are controllable,
    their unit (may override the global default), and bounds for the optimizer.
    """

    __tablename__ = "project_ingredients"
    __table_args__ = (UniqueConstraint("project_id", "ingredient_id", name="uq_project_ingredient"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingredients.id"), nullable=False
    )
    unit: Mapped[str | None] = mapped_column(String(32))
    min_amount: Mapped[float | None] = mapped_column(Float)
    max_amount: Mapped[float | None] = mapped_column(Float)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    project: Mapped[Project] = relationship(back_populates="ingredients")
    ingredient: Mapped[Ingredient] = relationship(back_populates="project_ingredients")
    formulation_ingredients: Mapped[list[FormulationIngredient]] = relationship(
        back_populates="project_ingredient"
    )


class FormulationIngredient(Base):
    """The actual amount of a specific ingredient in one formulation."""

    __tablename__ = "formulation_ingredients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    formulation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("formulations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_ingredient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_ingredients.id"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)

    formulation: Mapped[Formulation] = relationship(
        "Formulation",
        foreign_keys=[formulation_id],
        back_populates="ingredients",
    )
    project_ingredient: Mapped[ProjectIngredient] = relationship(
        back_populates="formulation_ingredients"
    )
