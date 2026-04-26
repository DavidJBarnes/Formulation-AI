from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from formulation_ai.auth import get_current_user
from formulation_ai.config import settings
from formulation_ai.db import get_db
from formulation_ai.models import (
    Formulation,
    FormulationIngredient,
    FormulationProperty,
    Ingredient,
    OutputProperty,
    Portfolio,
    Project,
    ProjectIngredient,
    ProjectStatus,
    ProjectTarget,
    User,
)
from formulation_ai.models.iteration import Iteration, IterationStatus
from formulation_ai.schemas.project import (
    FormulationRead,
    IngredientSpec,
    IterationSummary,
    LogResultsRequest,
    ParsedIngredientOut,
    ParsedProductOut,
    ParsedPropertyOut,
    ParsedTargetOut,
    ParsedUploadResponse,
    ProjectDetail,
    ProjectListItem,
    PropertyMeasurement,
    TargetSpec,
)
from formulation_ai.services.proposal_engine import ProposalRequest, run_proposal
from formulation_ai.services.xlsx_parser import parse_xlsx

_SAMPLE_PATH = Path(__file__).parent.parent.parent.parent.parent / "docs/upload-template/paint-example.xlsx"

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
        model_used=form.model_used,
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


@router.get("/sample-xlsx")
def get_sample_xlsx(_: User = Depends(get_current_user)) -> FileResponse:
    if not _SAMPLE_PATH.exists():
        raise HTTPException(status_code=404, detail="sample file not found")
    return FileResponse(
        path=str(_SAMPLE_PATH),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="paint-example.xlsx",
    )


@router.post("/parse-upload", response_model=ParsedUploadResponse)
async def parse_upload(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
) -> ParsedUploadResponse:
    data = await file.read()
    try:
        parsed = parse_xlsx(data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ParsedUploadResponse(
        ingredients=[ParsedIngredientOut(name=i.name, unit=i.unit) for i in parsed.ingredients],
        properties=[ParsedPropertyOut(name=p.name, unit=p.unit) for p in parsed.properties],
        base_products=[
            ParsedProductOut(label=bp.label, ingredients=bp.ingredients, properties=bp.properties)
            for bp in parsed.base_products
        ],
        targets=[
            ParsedTargetOut(property_name=t.property_name, goal=t.goal, reference_label=t.reference_label)
            for t in parsed.targets
        ],
    )


@router.post("/upload", response_model=ProjectDetail, status_code=201)
async def upload_project(
    file: UploadFile = File(...),
    name: str = Form(...),
    team: str = Form(""),
    domain: str = Form(""),
    started_at: str = Form(""),
    ends_at: str = Form(""),
    max_iterations: int = Form(6),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectDetail:
    data = await file.read()
    try:
        parsed = parse_xlsx(data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Ensure a portfolio exists
    portfolio = db.scalar(select(Portfolio))
    if not portfolio:
        portfolio = Portfolio(name="R&D Portfolio")
        db.add(portfolio)
        db.flush()

    from datetime import date as _date

    def _parse_date(s: str) -> _date | None:
        try:
            return _date.fromisoformat(s.strip()) if s.strip() else None
        except ValueError:
            return None

    # Create project
    project = Project(
        portfolio_id=portfolio.id,
        owner_id=current_user.id,
        owner_name=current_user.full_name or current_user.email,
        name=name.strip(),
        team=team.strip() or None,
        domain=domain.strip() or None,
        status=ProjectStatus.planning,
        started_at=_parse_date(started_at),
        ends_at=_parse_date(ends_at),
        max_iterations=max_iterations,
    )
    db.add(project)
    db.flush()

    # Get-or-create global ingredients, create project_ingredients
    name_to_pi: dict[str, ProjectIngredient] = {}
    for sort_i, ing in enumerate(parsed.ingredients):
        global_ing = db.scalar(select(Ingredient).where(Ingredient.name == ing.name))
        if not global_ing:
            global_ing = Ingredient(name=ing.name, default_unit=ing.unit)
            db.add(global_ing)
            db.flush()
        pi = ProjectIngredient(
            project_id=project.id,
            ingredient_id=global_ing.id,
            unit=ing.unit,
            sort_order=sort_i,
        )
        db.add(pi)
        db.flush()
        name_to_pi[ing.name] = pi

    # Get-or-create global output properties
    name_to_op: dict[str, OutputProperty] = {}
    for prop in parsed.properties:
        op = db.scalar(select(OutputProperty).where(OutputProperty.name == prop.name))
        if not op:
            op = OutputProperty(name=prop.name, default_unit=prop.unit)
            db.add(op)
            db.flush()
        name_to_op[prop.name] = op

    # Create project targets (from Targets sheet only)
    name_to_pt: dict[str, ProjectTarget] = {}
    for sort_i, tgt in enumerate(parsed.targets):
        op = name_to_op.get(tgt.property_name)
        if op is None:
            # Target references a property not in Products sheet — create the output_property anyway
            op = db.scalar(select(OutputProperty).where(OutputProperty.name == tgt.property_name))
            if not op:
                op = OutputProperty(name=tgt.property_name, default_unit=None)
                db.add(op)
                db.flush()
            name_to_op[tgt.property_name] = op
        pt = ProjectTarget(
            project_id=project.id,
            output_property_id=op.id,
            goal=tgt.goal,
            reference_label=tgt.reference_label,
            sort_order=sort_i,
        )
        db.add(pt)
        db.flush()
        name_to_pt[tgt.property_name] = pt

    # Create base formulations with ingredients and properties
    for bp in parsed.base_products:
        form = Formulation(
            project_id=project.id,
            label=bp.label,
            kind="base",
            iteration_id=None,
        )
        db.add(form)
        db.flush()

        for ing_name, amount in bp.ingredients.items():
            pi = name_to_pi.get(ing_name)
            if pi is None:
                continue
            db.add(FormulationIngredient(
                formulation_id=form.id,
                project_ingredient_id=pi.id,
                amount=amount,
            ))

        for prop_name, value in bp.properties.items():
            pt = name_to_pt.get(prop_name)
            if pt is None:
                continue
            db.add(FormulationProperty(
                formulation_id=form.id,
                project_target_id=pt.id,
                value=value,
            ))

    db.commit()
    db.expire_all()
    return get_project(project.id, db, current_user)


@router.post("/{project_id}/run-iteration", response_model=ProjectDetail)
def run_iteration(
    project_id: uuid.UUID,
    n_candidates: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectDetail:
    """Propose the next batch of candidate formulations using the LLM."""
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.iterations),
            selectinload(Project.targets).selectinload(ProjectTarget.output_property),
            selectinload(Project.ingredients).selectinload(ProjectIngredient.ingredient),
            selectinload(Project.formulations).selectinload(Formulation.ingredients),
            selectinload(Project.formulations).selectinload(Formulation.properties),
            selectinload(Project.formulations).selectinload(Formulation.iteration),
        )
    )
    project = db.scalar(stmt)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    current_n = max((it.n for it in project.iterations), default=0)
    next_n = current_n + 1
    if next_n > project.max_iterations:
        raise HTTPException(status_code=422, detail="project has reached max iterations")

    # Create the Iteration record
    from formulation_ai.models.iteration import IterationStatus
    iteration = Iteration(
        project_id=project.id,
        n=next_n,
        status=IterationStatus.in_progress,
    )
    db.add(iteration)
    db.flush()

    # Build lookup tables
    pi_id_to_name: dict[uuid.UUID, str] = {
        pi.id: pi.ingredient.name for pi in project.ingredients
    }
    pt_id_to_name: dict[uuid.UUID, tuple[str, str | None]] = {
        tgt.id: (tgt.output_property.name, tgt.output_property.default_unit)
        for tgt in project.targets
    }
    pt_by_name: dict[str, ProjectTarget] = {
        tgt.output_property.name: tgt for tgt in project.targets
    }
    pi_by_name: dict[str, ProjectIngredient] = {
        pi.ingredient.name: pi for pi in project.ingredients
    }
    iter_id_to_n: dict[uuid.UUID, int] = {it.id: it.n for it in project.iterations}

    # Build proposal request payload
    ingredients_payload = [
        {
            "name": pi.ingredient.name,
            "unit": pi.unit or pi.ingredient.default_unit or "",
            "min": pi.min_amount,
            "max": pi.max_amount,
        }
        for pi in sorted(project.ingredients, key=lambda x: x.sort_order)
    ]
    targets_payload = [
        {
            "property": tgt.output_property.name,
            "unit": tgt.output_property.default_unit or "",
            "goal": tgt.goal,
            "reference": tgt.reference_label,
            "weight": tgt.weight,
        }
        for tgt in sorted(project.targets, key=lambda x: x.sort_order)
    ]

    def _formulation_payload(f: Formulation) -> dict:
        ing = {
            pi_id_to_name[fi.project_ingredient_id]: fi.amount
            for fi in f.ingredients
            if fi.project_ingredient_id in pi_id_to_name
        }
        props = [
            {
                "name": pt_id_to_name[fp.project_target_id][0],
                "value": fp.value,
                "sigma": fp.sigma,
            }
            for fp in f.properties
            if fp.project_target_id in pt_id_to_name
        ]
        return {"label": f.label, "ingredients": ing, "properties": props}

    base_payload = [_formulation_payload(f) for f in project.formulations if f.kind == "base"]
    tested_payload = [
        {**_formulation_payload(f), "iteration": iter_id_to_n.get(f.iteration_id)}
        for f in sorted(project.formulations, key=lambda f: (iter_id_to_n.get(f.iteration_id) or 0, f.label))
        if f.kind == "tested"
    ]

    req = ProposalRequest(
        project_name=project.name,
        iteration_n=next_n,
        ingredients=ingredients_payload,
        targets=targets_payload,
        base_products=base_payload,
        tested=tested_payload,
        n_candidates=n_candidates,
        batch_total_g=project.batch_total_g,
    )

    try:
        proposals = run_proposal(req)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM proposal failed: {exc}") from exc

    # Persist proposed formulations
    for proposal in proposals:
        form = Formulation(
            project_id=project.id,
            iteration_id=iteration.id,
            label=proposal.label,
            kind="proposed",
            rationale=proposal.rationale,
            model_used=settings.anthropic_model,
        )
        db.add(form)
        db.flush()

        for ing_name, amount in proposal.ingredients.items():
            pi = pi_by_name.get(ing_name)
            if pi is None:
                continue
            db.add(FormulationIngredient(
                formulation_id=form.id,
                project_ingredient_id=pi.id,
                amount=amount,
            ))

        for pred in proposal.predictions:
            pt = pt_by_name.get(pred["property"])
            if pt is None:
                continue
            db.add(FormulationProperty(
                formulation_id=form.id,
                project_target_id=pt.id,
                value=float(pred["value"]),
                sigma=float(pred["sigma"]) if pred.get("sigma") is not None else None,
            ))

    # Advance project status from planning → iterating
    if project.status == ProjectStatus.planning:
        project.status = ProjectStatus.iterating

    db.commit()
    return get_project(project.id, db, current_user)


@router.post("/{project_id}/log-results", response_model=ProjectDetail)
def log_results(
    project_id: uuid.UUID,
    body: LogResultsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectDetail:
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.iterations),
            selectinload(Project.targets).selectinload(ProjectTarget.output_property),
            selectinload(Project.ingredients).selectinload(ProjectIngredient.ingredient),
            selectinload(Project.formulations).selectinload(Formulation.ingredients),
            selectinload(Project.formulations).selectinload(Formulation.properties),
            selectinload(Project.formulations).selectinload(Formulation.iteration),
        )
    )
    project = db.scalar(stmt)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    if body.iteration_n < 1 or body.iteration_n > project.max_iterations:
        raise HTTPException(status_code=422, detail="iteration_n out of range")

    if not body.results:
        raise HTTPException(status_code=422, detail="results cannot be empty")

    # Find or create the Iteration record
    iteration = next((it for it in project.iterations if it.n == body.iteration_n), None)
    if not iteration:
        iteration = Iteration(
            project_id=project.id,
            n=body.iteration_n,
            status=IterationStatus.in_progress,
        )
        db.add(iteration)
        db.flush()

    # Lookup tables
    pt_by_name: dict[str, ProjectTarget] = {
        tgt.output_property.name: tgt for tgt in project.targets
    }
    proposals_by_id: dict[uuid.UUID, Formulation] = {
        f.id: f for f in project.formulations if f.kind == "proposed"
    }
    base_by_label: dict[str, dict[uuid.UUID, float]] = {
        f.label: {fp.project_target_id: fp.value for fp in f.properties}
        for f in project.formulations
        if f.kind == "base"
    }

    any_flagged = False
    all_flag_reasons: list[str] = []
    targets_met_best = 0

    for idx, entry in enumerate(body.results):
        proposal = proposals_by_id.get(entry.proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail=f"proposal {entry.proposal_id} not found")

        # Check deviation against predicted ± sigma
        predicted: dict[uuid.UUID, tuple[float, float | None]] = {
            fp.project_target_id: (fp.value, fp.sigma) for fp in proposal.properties
        }
        flagged = False
        flag_reasons: list[str] = []
        for prop_name, measured in entry.properties.items():
            pt = pt_by_name.get(prop_name)
            if pt is None:
                continue
            pred_entry = predicted.get(pt.id)
            if pred_entry and pred_entry[1] is not None and pred_entry[1] > 0:
                pred_val, sigma = pred_entry
                if abs(measured - pred_val) > 2 * sigma:
                    flagged = True
                    flag_reasons.append(
                        f"{proposal.label}/{prop_name}: predicted {pred_val:.3g}±{sigma:.3g}, got {measured:.3g}"
                    )

        if flagged:
            any_flagged = True
            all_flag_reasons.extend(flag_reasons)

        # Build tested formulation label
        existing_tested = sum(
            1 for f in project.formulations
            if f.kind == "tested" and f.iteration_id == iteration.id
        )
        tested_label = f"T-{body.iteration_n}-{existing_tested + idx + 1}"

        tested_form = Formulation(
            project_id=project.id,
            iteration_id=iteration.id,
            label=tested_label,
            kind="tested",
            flagged=flagged,
        )
        db.add(tested_form)
        db.flush()

        # Copy ingredient amounts from proposal
        for fi in proposal.ingredients:
            db.add(FormulationIngredient(
                formulation_id=tested_form.id,
                project_ingredient_id=fi.project_ingredient_id,
                amount=fi.amount,
            ))

        # Record measured property values
        for prop_name, measured_val in entry.properties.items():
            pt = pt_by_name.get(prop_name)
            if pt is None:
                continue
            db.add(FormulationProperty(
                formulation_id=tested_form.id,
                project_target_id=pt.id,
                value=measured_val,
            ))

        # Compute targets met for this formulation
        met = 0
        for tgt in project.targets:
            measured = entry.properties.get(tgt.output_property.name)
            if measured is None:
                continue
            ref: float | None = None
            if tgt.reference_label:
                ref = base_by_label.get(tgt.reference_label, {}).get(tgt.id)
            if _evaluate_goal(tgt.goal, measured, ref):
                met += 1
        targets_met_best = max(targets_met_best, met)

    # Mark iteration done and record best objective
    iteration.status = IterationStatus.done
    total_targets = len(project.targets)
    iteration.best_objective = (targets_met_best / total_targets) if total_targets > 0 else 0.0

    # Auto-transition project status
    if targets_met_best >= total_targets > 0:
        project.status = ProjectStatus.converged
        project.flag_note = None
    elif any_flagged:
        project.status = ProjectStatus.flagged
        project.flag_note = "; ".join(all_flag_reasons[:3])
    else:
        project.status = ProjectStatus.iterating
        project.flag_note = None

    db.commit()
    return get_project(project.id, db, current_user)


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
