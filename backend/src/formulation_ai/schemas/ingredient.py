from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IngredientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    default_unit: str | None = Field(default=None, max_length=32)
    description: str | None = None


class IngredientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    default_unit: str | None = Field(default=None, max_length=32)
    description: str | None = None


class IngredientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    default_unit: str | None
    description: str | None
    created_at: datetime
    project_count: int = 0
