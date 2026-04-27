from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from formulation_ai.models.base import Base


class UserAbility(Base):
    __tablename__ = "user_abilities"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    ability_key: Mapped[str] = mapped_column(
        String(128), ForeignKey("abilities.key", ondelete="CASCADE"), primary_key=True
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="user_abilities")  # noqa: F821
    ability: Mapped[Ability] = relationship(back_populates="user_abilities")  # noqa: F821
