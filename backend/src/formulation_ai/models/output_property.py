from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from formulation_ai.models.base import Base

if TYPE_CHECKING:
    from formulation_ai.models.formulation import Formulation
    from formulation_ai.models.project import Project


class OutputProperty(Base):
    """Global registry of measurable outputs — reusable across projects."""

    __tablename__ = "output_properties"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(256), unique=True, nullable=False, index=True)
    default_unit: Mapped[str | None] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project_targets: Mapped[list[ProjectTarget]] = relationship(back_populates="output_property")


class ProjectTarget(Base):
    """
    A goal for one output property within a project.

    goal uses the mini-DSL: ">=0.92", "<=15", "+10%", "-5%", "=7.4", "[5,10]".
    reference_label names the base formulation used for relative (%) goals —
    stored as text for now; can be upgraded to a FK to formulations later.
    """

    __tablename__ = "project_targets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    output_property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("output_properties.id"), nullable=False
    )
    goal: Mapped[str] = mapped_column(String(64), nullable=False)
    reference_label: Mapped[str | None] = mapped_column(String(256))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    project: Mapped[Project] = relationship(back_populates="targets")
    output_property: Mapped[OutputProperty] = relationship(back_populates="project_targets")
    formulation_properties: Mapped[list[FormulationProperty]] = relationship(
        back_populates="project_target",
        primaryjoin="FormulationProperty.project_target_id == ProjectTarget.id",
    )


class FormulationProperty(Base):
    """
    A measured or predicted output value for one formulation.
    sigma is populated for proposed (AI-generated) formulations only.
    """

    __tablename__ = "formulation_properties"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    formulation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("formulations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_target_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_targets.id"), nullable=False
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    sigma: Mapped[float | None] = mapped_column(Float)

    formulation: Mapped[Formulation] = relationship(
        "Formulation",
        foreign_keys=[formulation_id],
        back_populates="properties",
    )
    project_target: Mapped[ProjectTarget] = relationship(
        back_populates="formulation_properties",
        primaryjoin="FormulationProperty.project_target_id == ProjectTarget.id",
    )
