from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class IterationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    n: int
    best_objective: float | None
    status: str
    note: str | None = None
    started_at: datetime | None = None


class IngredientSpec(BaseModel):
    name: str
    unit: str | None
    min_amount: float | None = None
    max_amount: float | None = None


class TargetSpec(BaseModel):
    property_name: str
    unit: str | None
    goal: str
    reference_label: str | None = None


class PropertyMeasurement(BaseModel):
    name: str
    unit: str | None
    value: float
    sigma: float | None = None


class FormulationRead(BaseModel):
    id: uuid.UUID
    label: str
    kind: str
    iteration_n: int | None = None
    rationale: str | None = None
    model_used: str | None = None
    flagged: bool = False
    ingredients: dict[str, float] = {}
    properties: list[PropertyMeasurement] = []


class ProjectListItem(BaseModel):
    id: uuid.UUID
    name: str
    team_name: str | None
    owner_name: str | None
    status: str
    started_at: date | None
    ends_at: date | None
    domain: str | None
    current_iteration: int
    max_iterations: int
    targets_met: int
    targets_total: int
    iterations: list[IterationSummary] = []


class ProjectDetail(ProjectListItem):
    flag_note: str | None = None
    ingredients: list[IngredientSpec] = []
    targets: list[TargetSpec] = []
    base_products: list[FormulationRead] = []
    tested: list[FormulationRead] = []
    proposed: list[FormulationRead] = []


# Upload / parse responses


class ParsedIngredientOut(BaseModel):
    name: str
    unit: str | None


class ParsedPropertyOut(BaseModel):
    name: str
    unit: str | None


class ParsedProductOut(BaseModel):
    label: str
    ingredients: dict[str, float] = {}
    properties: dict[str, float] = {}


class ParsedTargetOut(BaseModel):
    property_name: str
    goal: str
    reference_label: str | None = None


class ParsedUploadResponse(BaseModel):
    ingredients: list[ParsedIngredientOut]
    properties: list[ParsedPropertyOut]
    base_products: list[ParsedProductOut]
    targets: list[ParsedTargetOut]


# Log-results request

class FormulationResultEntry(BaseModel):
    proposal_id: uuid.UUID
    properties: dict[str, float]  # property_name -> measured value


class LogResultsRequest(BaseModel):
    iteration_n: int
    results: list[FormulationResultEntry]
