from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from formulation_ai.models.base import Base

if TYPE_CHECKING:
    from formulation_ai.models.ingredient import FormulationIngredient
    from formulation_ai.models.iteration import Iteration
    from formulation_ai.models.output_property import FormulationProperty
    from formulation_ai.models.project import Project


class FormulationKind(enum.StrEnum):
    base = "base"
    tested = "tested"
    proposed = "proposed"


class Formulation(Base):
    """
    A specific formulation recipe — base product, lab-tested result, or AI proposal.

    Base formulations have iteration_id = None.
    Proposed formulations carry AI rationale and sigma values on their properties.
    Flagged formulations have results that deviate beyond the noise threshold.
    """

    __tablename__ = "formulations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    iteration_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("iterations.id", ondelete="SET NULL"), index=True
    )
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[FormulationKind] = mapped_column(
        SAEnum(FormulationKind, native_enum=False, length=16), nullable=False
    )
    rationale: Mapped[str | None] = mapped_column(Text)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="formulations")
    iteration: Mapped[Iteration | None] = relationship(back_populates="formulations")
    ingredients: Mapped[list[FormulationIngredient]] = relationship(
        "FormulationIngredient",
        foreign_keys="FormulationIngredient.formulation_id",
        back_populates="formulation",
        cascade="all, delete-orphan",
    )
    properties: Mapped[list[FormulationProperty]] = relationship(
        "FormulationProperty",
        foreign_keys="FormulationProperty.formulation_id",
        back_populates="formulation",
        cascade="all, delete-orphan",
    )
