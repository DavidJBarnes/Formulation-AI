"""Admin router — user/ability management.

Ability management routes require is_admin.
User management routes require manage_users ability (or is_admin).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import exc as sa_exc
from sqlalchemy.orm import Session

from formulation_ai.auth import get_current_admin, hash_password, require_ability
from formulation_ai.db import get_db
from formulation_ai.models import Ability, AppSetting, User, UserAbility

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
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool
    is_admin: bool
    abilities: list[str] = []


class AdminUserCreate(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=6, max_length=128)
    first_name: str | None = None
    last_name: str | None = None
    is_admin: bool = False


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
    _: User = Depends(require_ability("manage_users")),
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


# ---------------------------------------------------------------------------
# User management (requires manage_users ability)
# ---------------------------------------------------------------------------

@router.post(
    "/users",
    response_model=UserWithAbilities,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ability("manage_users")),
) -> User:
    # Only admins may create admin accounts
    if payload.is_admin and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create admin accounts",
        )
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        full_name=_build_full_name(payload.first_name, payload.last_name),
        is_admin=payload.is_admin,
    )
    db.add(user)
    try:
        db.commit()
    except sa_exc.IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=400, detail="email already registered") from err
    db.refresh(user)
    return user


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ability("manage_users")),
) -> None:
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="cannot delete yourself")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()


def _build_full_name(first_name: str | None, last_name: str | None) -> str | None:
    parts = [p for p in (first_name, last_name) if p]
    return " ".join(parts) if parts else None


# ---------------------------------------------------------------------------
# App settings schemas
# ---------------------------------------------------------------------------

class ProviderSettingsOut(BaseModel):
    """Returned by GET /admin/settings — masks the actual API key."""

    model_config = ConfigDict(from_attributes=True)

    provider: str
    api_key_set: bool
    model: str


class ProviderSettingsIn(BaseModel):
    """Accepted by PUT /admin/settings."""

    provider: str
    api_key: str | None = None
    model: str | None = None


# ---------------------------------------------------------------------------
# App settings endpoints (admin only)
# ---------------------------------------------------------------------------

@router.get("/settings", response_model=ProviderSettingsOut)
def get_settings(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> ProviderSettingsOut:
    """Return current LLM provider configuration. API key is never exposed."""
    stored = {
        row.key: row.value
        for row in db.query(AppSetting).filter(
            AppSetting.key.in_(["llm_provider", "llm_api_key", "llm_model"])
        ).all()
    }

    provider = stored.get("llm_provider", "anthropic")
    api_key_set = bool(stored.get("llm_api_key"))
    model = stored.get("llm_model")
    if model is None:
        model = "claude-sonnet-4-6" if provider == "anthropic" else "deepseek-chat"

    return ProviderSettingsOut(
        provider=provider,
        api_key_set=api_key_set,
        model=model,
    )


@router.put("/settings", response_model=ProviderSettingsOut)
def update_settings(
    payload: ProviderSettingsIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> ProviderSettingsOut:
    """Update LLM provider configuration."""
    if payload.provider not in ("anthropic", "deepseek"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="provider must be 'anthropic' or 'deepseek'",
        )

    def _upsert(key: str, value: str) -> None:
        row = db.get(AppSetting, key)
        if row:
            row.value = value
        else:
            db.add(AppSetting(key=key, value=value))

    _upsert("llm_provider", payload.provider)

    if payload.api_key is not None:
        _upsert("llm_api_key", payload.api_key)

    if payload.model is not None:
        _upsert("llm_model", payload.model)

    db.commit()

    api_key_set = bool(
        db.get(AppSetting, "llm_api_key")
        and db.get(AppSetting, "llm_api_key").value  # type: ignore[union-attr]
    )
    return ProviderSettingsOut(
        provider=payload.provider,
        api_key_set=api_key_set,
        model=payload.model or ("claude-sonnet-4-6" if payload.provider == "anthropic" else "deepseek-chat"),
    )
