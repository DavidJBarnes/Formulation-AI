from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from formulation_ai.auth import get_current_user
from formulation_ai.db import get_db
from formulation_ai.models import User
from formulation_ai.models.formulation import Formulation
from formulation_ai.models.ingredient import ProjectIngredient
from formulation_ai.models.output_property import ProjectTarget
from formulation_ai.models.project import Project
from formulation_ai.schemas.project import (
    FormulationRead,
    IngredientSpec,
    IterationSummary,
    ProjectDetail,
    ProjectListItem,
    PropertyMeasurement,
    TargetSpec,
)

router = APIRouter(prefix="/projects", tags=["projects"])


# ---------------------------------------------------------------------------
# Goal evaluation helper
# ---------------------------------------------------------------------------


def _evaluate_goal(goal: str, value: float, ref: float | None) -> bool:
    """Return True when `value` satisfies `goal`."""
    trimmed = re.sub(r"\s", "", goal)

    if trimmed.startswith(">="):
        return value >= float(trimmed[2:])
    if trimmed.startswith("<="):
        return value <= float(trimmed[2:])
    if trimmed.startswith("="):
        n = float(trimmed[1:])
        return abs(value - n) < 0.001
    # ±N%
    pct_match = re.fullmatch(r"([+-]\d+(?:\.\d+)?)%", trimmed)
    if pct_match:
        if ref is None:
            return False
        pct = float(pct_match.group(1)) / 100.0
        target = ref * (1 + pct)
        return value >= target if pct >= 0 else value <= target
    # [N,M]
    range_match = re.fullmatch(r"\[(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\]", trimmed)
    if range_match:
        return float(range_match.group(1)) <= value <= float(range_match.group(2))
    return False


# ---------------------------------------------------------------------------
# Internal builders
# ---------------------------------------------------------------------------


def _build_formulation_read(
    form: Formulation,
    pi_id_to_name: dict[uuid.UUID, str],
    pt_id_to_name: dict[uuid.UUID, tuple[str, str | None]],
    iteration_n: int | None,
) -> FormulationRead:
    ingredients: dict[str, float] = {}
    for fi in form.ingredients:
        name = pi_id_to_name.get(fi.project_ingredient_id)
        if name is not None:
            ingredients[name] = fi.amount

    properties: list[PropertyMeasurement] = []
    for fp in form.properties:
        prop_name, prop_unit = pt_id_to_name.get(fp.project_target_id, ("?", None))
        properties.append(PropertyMeasurement(name=prop_name, unit=prop_unit, value=fp.value, sigma=fp.sigma))

    return FormulationRead(
        id=form.id,
        label=form.label,
        kind=form.kind,
        iteration_n=iteration_n,
        rationale=form.rationale,
        flagged=form.flagged,
        ingredients=ingredients,
        properties=properties,
    )


def _targets_met(
    project: Project,
    db: Session,
) -> int:
    """Count how many project targets are met by the latest tested formulation."""
    targets: list[ProjectTarget] = project.targets
    if not targets:
        return 0

    # Build a lookup: label -> { pt_id -> value } for base formulations
    base_by_label: dict[str, dict[uuid.UUID, float]] = {}
    tested_by_iter: list[tuple[int, Formulation]] = []

    for form in project.formulations:
        if form.kind == "base":
            prop_map: dict[uuid.UUID, float] = {fp.project_target_id: fp.value for fp in form.properties}
            base_by_label[form.label] = prop_map
        elif form.kind == "tested" and form.iteration is not None:
            tested_by_iter.append((form.iteration.n, form))

    # Latest tested iteration number
    if not tested_by_iter:
        return 0
    max_n = max(n for n, _ in tested_by_iter)
    latest_tested = [f for n, f in tested_by_iter if n == max_n]

    # Build lookup: pt_id -> value from latest tested (first formulation with the value wins)
    latest_values: dict[uuid.UUID, float] = {}
    for form in latest_tested:
        for fp in form.properties:
            if fp.project_target_id not in latest_values:
                latest_values[fp.project_target_id] = fp.value

    count = 0
    for tgt in targets:
        value = latest_values.get(tgt.id)
        if value is None:
            continue
        # Look up reference value from base formulation
        ref: float | None = None
        if tgt.reference_label:
            ref_props = base_by_label.get(tgt.reference_label, {})
            ref = ref_props.get(tgt.id)
        if _evaluate_goal(tgt.goal, value, ref):
            count += 1
    return count


def _project_to_list_item(project: Project) -> ProjectListItem:
    iterations_sorted = sorted(project.iterations, key=lambda i: i.n)
    current_iteration = max((i.n for i in iterations_sorted), default=0)

    targets_total = len(project.targets)
    targets_met = _targets_met_from_loaded(project)

    return ProjectListItem(
        id=project.id,
        name=project.name,
        team=project.team,
        owner_name=project.owner_name,
        status=project.status,
        started_at=project.started_at,
        ends_at=project.ends_at,
        domain=project.domain,
        current_iteration=current_iteration,
        max_iterations=project.max_iterations,
        targets_met=targets_met,
        targets_total=targets_total,
        iterations=[
            IterationSummary(
                n=it.n,
                best_objective=it.best_objective,
                status=it.status,
                note=it.note,
            )
            for it in iterations_sorted
        ],
    )


def _targets_met_from_loaded(project: Project) -> int:
    """Count targets met — uses already-loaded relationships."""
    targets = project.targets
    if not targets:
        return 0

    base_by_label: dict[str, dict[uuid.UUID, float]] = {}
    tested_by_iter: list[tuple[int, Formulation]] = []

    for form in project.formulations:
        if form.kind == "base":
            base_by_label[form.label] = {fp.project_target_id: fp.value for fp in form.properties}
        elif form.kind == "tested" and form.iteration is not None:
            tested_by_iter.append((form.iteration.n, form))

    if not tested_by_iter:
        return 0

    max_n = max(n for n, _ in tested_by_iter)
    latest_tested = [f for n, f in tested_by_iter if n == max_n]

    latest_values: dict[uuid.UUID, float] = {}
    for form in latest_tested:
        for fp in form.properties:
            if fp.project_target_id not in latest_values:
                latest_values[fp.project_target_id] = fp.value

    count = 0
    for tgt in targets:
        value = latest_values.get(tgt.id)
        if value is None:
            continue
        ref: float | None = None
        if tgt.reference_label:
            ref = base_by_label.get(tgt.reference_label, {}).get(tgt.id)
        if _evaluate_goal(tgt.goal, value, ref):
            count += 1
    return count


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=list[ProjectListItem])
def list_projects(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ProjectListItem]:
    stmt = (
        select(Project)
        .options(
            selectinload(Project.iterations),
            selectinload(Project.targets).selectinload(ProjectTarget.output_property),
            selectinload(Project.formulations).selectinload(Formulation.properties),
            selectinload(Project.formulations).selectinload(Formulation.iteration),
        )
        .order_by(Project.started_at.desc().nullslast())
    )
    projects = db.scalars(stmt).all()
    return [_project_to_list_item(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ProjectDetail:
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.iterations),
            selectinload(Project.targets).selectinload(ProjectTarget.output_property),
            selectinload(Project.ingredients).selectinload(ProjectIngredient.ingredient),
            selectinload(Project.formulations)
            .selectinload(Formulation.ingredients),
            selectinload(Project.formulations)
            .selectinload(Formulation.properties),
            selectinload(Project.formulations)
            .selectinload(Formulation.iteration),
        )
    )
    project = db.scalar(stmt)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    iterations_sorted = sorted(project.iterations, key=lambda i: i.n)
    current_iteration = max((i.n for i in iterations_sorted), default=0)
    targets_total = len(project.targets)
    targets_met = _targets_met_from_loaded(project)

    # Build lookup dicts for formulation assembly
    pi_id_to_name: dict[uuid.UUID, str] = {
        pi.id: pi.ingredient.name for pi in project.ingredients
    }
    pt_id_to_name: dict[uuid.UUID, tuple[str, str | None]] = {
        tgt.id: (tgt.output_property.name, tgt.output_property.default_unit)
        for tgt in project.targets
    }
    iter_id_to_n: dict[uuid.UUID, int] = {it.id: it.n for it in project.iterations}

    base_products: list[FormulationRead] = []
    tested: list[FormulationRead] = []
    proposed: list[FormulationRead] = []

    for form in project.formulations:
        iter_n = iter_id_to_n.get(form.iteration_id) if form.iteration_id else None
        read = _build_formulation_read(form, pi_id_to_name, pt_id_to_name, iter_n)
        if form.kind == "base":
            base_products.append(read)
        elif form.kind == "tested":
            tested.append(read)
        elif form.kind == "proposed":
            proposed.append(read)

    tested.sort(key=lambda f: (f.iteration_n or 0, f.label))
    proposed.sort(key=lambda f: (f.iteration_n or 0, f.label))

    return ProjectDetail(
        id=project.id,
        name=project.name,
        team=project.team,
        owner_name=project.owner_name,
        status=project.status,
        started_at=project.started_at,
        ends_at=project.ends_at,
        domain=project.domain,
        current_iteration=current_iteration,
        max_iterations=project.max_iterations,
        targets_met=targets_met,
        targets_total=targets_total,
        flag_note=project.flag_note,
        iterations=[
            IterationSummary(n=it.n, best_objective=it.best_objective, status=it.status, note=it.note)
            for it in iterations_sorted
        ],
        ingredients=[
            IngredientSpec(
                name=pi.ingredient.name,
                unit=pi.unit or pi.ingredient.default_unit,
                min_amount=pi.min_amount,
                max_amount=pi.max_amount,
            )
            for pi in sorted(project.ingredients, key=lambda x: x.sort_order)
        ],
        targets=[
            TargetSpec(
                property_name=tgt.output_property.name,
                unit=tgt.output_property.default_unit,
                goal=tgt.goal,
                reference_label=tgt.reference_label,
            )
            for tgt in sorted(project.targets, key=lambda x: x.sort_order)
        ],
        base_products=base_products,
        tested=tested,
        proposed=proposed,
    )
