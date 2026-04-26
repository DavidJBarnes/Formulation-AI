from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from formulation_ai.auth import get_current_user
from formulation_ai.db import get_db
from formulation_ai.models import Ingredient, ProjectIngredient, User
from formulation_ai.schemas.ingredient import IngredientCreate, IngredientRead, IngredientUpdate

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


def _to_read(ingredient: Ingredient, db: Session) -> IngredientRead:
    count = db.scalar(
        select(func.count()).where(ProjectIngredient.ingredient_id == ingredient.id)
    ) or 0
    return IngredientRead(
        id=ingredient.id,
        name=ingredient.name,
        default_unit=ingredient.default_unit,
        description=ingredient.description,
        created_at=ingredient.created_at,
        project_count=count,
    )


@router.get("", response_model=list[IngredientRead])
def list_ingredients(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[IngredientRead]:
    rows = db.scalars(select(Ingredient).order_by(Ingredient.name)).all()
    return [_to_read(r, db) for r in rows]


@router.post("", response_model=IngredientRead, status_code=status.HTTP_201_CREATED)
def create_ingredient(
    payload: IngredientCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> IngredientRead:
    existing = db.scalar(select(Ingredient).where(Ingredient.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail="ingredient name already exists")
    ingredient = Ingredient(**payload.model_dump())
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)
    return _to_read(ingredient, db)


@router.patch("/{ingredient_id}", response_model=IngredientRead)
def update_ingredient(
    ingredient_id: uuid.UUID,
    payload: IngredientUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> IngredientRead:
    ingredient = db.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="ingredient not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ingredient, field, value)
    db.commit()
    db.refresh(ingredient)
    return _to_read(ingredient, db)


@router.delete("/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(
    ingredient_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    ingredient = db.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="ingredient not found")
    in_use = db.scalar(
        select(func.count()).where(ProjectIngredient.ingredient_id == ingredient_id)
    ) or 0
    if in_use:
        raise HTTPException(
            status_code=409,
            detail=f"ingredient is used in {in_use} project(s) — remove it from those projects first",
        )
    db.delete(ingredient)
    db.commit()
