"""Teams router — list and create teams."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from formulation_ai.auth import get_current_user, require_ability
from formulation_ai.db import get_db
from formulation_ai.models import Team, User

router = APIRouter(prefix="/teams", tags=["teams"])


class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str


class TeamCreate(BaseModel):
    name: str


@router.get("", response_model=list[TeamOut])
def list_teams(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Team]:
    return db.query(Team).order_by(Team.name).all()


@router.post("", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
def create_team(
    payload: TeamCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_ability("manage_users")),
) -> Team:
    existing = db.query(Team).filter(Team.name == payload.name.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Team already exists")
    team = Team(name=payload.name.strip())
    db.add(team)
    db.commit()
    db.refresh(team)
    return team
