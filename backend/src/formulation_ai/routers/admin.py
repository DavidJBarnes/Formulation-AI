"""Admin router — user/ability management. All routes require is_admin."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from formulation_ai.auth import get_current_admin
from formulation_ai.db import get_db
from formulation_ai.models import Ability, User, UserAbility

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Schemas (local — admin-only, no need to share with other modules)
# ---------------------------------------------------------------------------

class AbilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    key: str
    description: str | None


class AbilityCreate(BaseModel):
    key: str
    description: str | None = None


class UserWithAbilities(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    full_name: str | None
    is_active: bool
    is_admin: bool
    abilities: list[str] = []


# ---------------------------------------------------------------------------
# Ability endpoints
# ---------------------------------------------------------------------------

@router.get("/abilities", response_model=list[AbilityOut])
def list_abilities(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> list[Ability]:
    return db.query(Ability).order_by(Ability.key).all()


@router.post("/abilities", response_model=AbilityOut, status_code=status.HTTP_201_CREATED)
def create_ability(
    payload: AbilityCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> Ability:
    if db.get(Ability, payload.key):
        raise HTTPException(status_code=400, detail=f"Ability '{payload.key}' already exists")
    ability = Ability(key=payload.key, description=payload.description)
    db.add(ability)
    db.commit()
    db.refresh(ability)
    return ability


# ---------------------------------------------------------------------------
# User × ability endpoints
# ---------------------------------------------------------------------------

@router.get("/users", response_model=list[UserWithAbilities])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> list[User]:
    return db.query(User).order_by(User.email).all()


@router.post(
    "/users/{user_id}/abilities/{ability_key}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def grant_ability(
    user_id: uuid.UUID,
    ability_key: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> None:
    if not db.get(User, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    if not db.get(Ability, ability_key):
        raise HTTPException(status_code=404, detail="Ability not found")
    existing = db.get(UserAbility, {"user_id": user_id, "ability_key": ability_key})
    if not existing:
        db.add(UserAbility(user_id=user_id, ability_key=ability_key))
        db.commit()


@router.delete(
    "/users/{user_id}/abilities/{ability_key}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_ability(
    user_id: uuid.UUID,
    ability_key: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> None:
    row = db.get(UserAbility, {"user_id": user_id, "ability_key": ability_key})
    if row:
        db.delete(row)
        db.commit()
