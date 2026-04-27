from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from formulation_ai.models.base import Base


class Ability(Base):
    __tablename__ = "abilities"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    description: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user_abilities: Mapped[list[UserAbility]] = relationship(  # noqa: F821
        back_populates="ability", cascade="all, delete-orphan"
    )
