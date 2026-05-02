from __future__ import annotations

import enum
import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from formulation_ai.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from formulation_ai.models.formulation import Formulation
    from formulation_ai.models.ingredient import ProjectIngredient
    from formulation_ai.models.iteration import Iteration
    from formulation_ai.models.output_property import ProjectTarget
    from formulation_ai.models.portfolio import Portfolio
    from formulation_ai.models.team import Team
    from formulation_ai.models.user import User


class ProjectStatus(enum.StrEnum):
    planning = "planning"
    iterating = "iterating"
    converged = "converged"
    flagged = "flagged"


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(128))
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL")
    )
    status: Mapped[ProjectStatus] = mapped_column(
        SAEnum(ProjectStatus, native_enum=False, length=16),
        default=ProjectStatus.planning,
        nullable=False,
    )
    started_at: Mapped[date | None] = mapped_column(Date)
    ends_at: Mapped[date | None] = mapped_column(Date)
    max_iterations: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    batch_total_g: Mapped[float | None] = mapped_column(Float)
    flag_note: Mapped[str | None] = mapped_column(Text)

    portfolio: Mapped[Portfolio] = relationship(back_populates="projects")
    owner: Mapped[User | None] = relationship()
    team: Mapped[Team | None] = relationship(back_populates="projects")
    ingredients: Mapped[list[ProjectIngredient]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectIngredient.sort_order",
    )
    targets: Mapped[list[ProjectTarget]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectTarget.sort_order",
    )
    iterations: Mapped[list[Iteration]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Iteration.n",
    )
    formulations: Mapped[list[Formulation]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
