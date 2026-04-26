from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from formulation_ai.models.base import Base

if TYPE_CHECKING:
    from formulation_ai.models.formulation import Formulation
    from formulation_ai.models.project import Project


class IterationStatus(enum.StrEnum):
    queued = "queued"
    in_progress = "in_progress"
    done = "done"


class Iteration(Base):
    """
    One cycle of the DOE inner loop within a project.
    n is 1-based and unique per project.
    """

    __tablename__ = "iterations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    n: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[IterationStatus] = mapped_column(
        SAEnum(IterationStatus, native_enum=False, length=16),
        default=IterationStatus.queued,
        nullable=False,
    )
    best_objective: Mapped[float | None] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="iterations")
    formulations: Mapped[list[Formulation]] = relationship(back_populates="iteration")
