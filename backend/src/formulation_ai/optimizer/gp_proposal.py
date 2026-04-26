"""
GP-backed proposal runner.

Takes the same ProposalRequest as the LLM engine and returns the same
ProposedFormulation list. Predictions come from the GP posterior;
the LLM is called only to generate rationale for each candidate.
"""

from __future__ import annotations

import json
import re

import anthropic
import numpy as np

from formulation_ai.config import settings
from formulation_ai.optimizer.candidate_selector import select_candidates
from formulation_ai.optimizer.gp_model import GPModel
from formulation_ai.optimizer.scaler import Scaler
from formulation_ai.services.proposal_engine import ProposalRequest, ProposedFormulation


def run_gp_proposal(req: ProposalRequest) -> list[ProposedFormulation]:
    """Fit GP on tested data, select candidates, ask LLM for rationale only."""
    ing_names = [i["name"] for i in req.ingredients]
    target_names = [t["property"] for t in req.targets]
    weights = [t.get("weight", 1.0) for t in req.targets]
    weight_arr = np.array(weights, dtype=float)
    if weight_arr.sum() > 0:
        weight_arr = weight_arr / weight_arr.sum()

    # --- Build training data from tested formulations ---
    X_raw: list[list[float]] = []
    y_raw: list[float] = []

    for form in req.tested:
        row = [form["ingredients"].get(n, 0.0) for n in ing_names]
        # Scalarize targets: weighted average of normalized property values
        prop_vals = []
        for t, w in zip(req.targets, weight_arr, strict=True):
            v = next((p["value"] for p in form.get("properties", []) if p["name"] == t["property"]), None)
            prop_vals.append((v, w))
        if all(v is not None for v, _ in prop_vals):
            score = sum(v * w for v, w in prop_vals)  # type: ignore[operator]
            X_raw.append(row)
            y_raw.append(score)

    X = np.array(X_raw)
    y = np.array(y_raw)

    # --- Fit scalers ---
    x_scaler = Scaler().fit(X)
    X_scaled = x_scaler.transform(X)

    y_scaler = Scaler().fit(y.reshape(-1, 1))
    y_scaled = y_scaler.transform(y.reshape(-1, 1)).ravel()

    # --- Fit GP ---
    gp = GPModel(n_restarts=settings.optimizer_n_restarts, random_seed=settings.optimizer_random_seed)
    gp.fit(X_scaled, y_scaled)

    # --- Build ingredient bounds in scaled space ---
    ing_bounds_raw: list[tuple[float, float]] = []
    for i, ing in enumerate(req.ingredients):
        lo = ing.get("min") if ing.get("min") is not None else float(x_scaler.min_[i])  # type: ignore[index]
        hi = ing.get("max") if ing.get("max") is not None else float(x_scaler.max_[i])  # type: ignore[index]
        ing_bounds_raw.append((lo, hi))

    # Scale bounds
    lo_arr = np.array([b[0] for b in ing_bounds_raw])
    hi_arr = np.array([b[1] for b in ing_bounds_raw])
    span = x_scaler.max_ - x_scaler.min_  # type: ignore[operator]
    span[span == 0] = 1.0
    lo_scaled = (lo_arr - x_scaler.min_) / span  # type: ignore[operator]
    hi_scaled = (hi_arr - x_scaler.min_) / span  # type: ignore[operator]
    bounds_scaled = [(max(0.0, float(lo)), min(1.0, float(hi))) for lo, hi in zip(lo_scaled, hi_scaled, strict=True)]

    # Batch sum constraint in scaled space
    batch_constraint_scaled: float | None = None
    if req.batch_total_g is not None:
        batch_arr = np.array([[req.batch_total_g] * len(ing_names)])
        batch_constraint_scaled = float(x_scaler.transform(batch_arr)[0].sum() / len(ing_names))

    y_best = float(y_scaled.max())

    candidates = select_candidates(
        gp=gp,
        x_scaler=x_scaler,
        n_ingredients=len(ing_names),
        n_candidates=req.n_candidates,
        y_best=y_best,
        bounds_scaled=bounds_scaled,
        batch_constraint=batch_constraint_scaled,
        acq=settings.optimizer_acquisition,
        kappa=settings.optimizer_ucb_kappa,
        xi=settings.optimizer_ei_xi,
        n_restarts=settings.optimizer_n_restarts,
        random_seed=settings.optimizer_random_seed,
    )

    # --- Convert candidates back to raw ingredient amounts ---
    raw_candidates = []
    for i, cand in enumerate(candidates):
        ing_amounts_scaled = cand.ingredients_scaled.reshape(1, -1)
        ing_amounts_raw = x_scaler.inverse_transform(ing_amounts_scaled).ravel()

        # Per-property predictions: fit individual GPs per target property
        prop_predictions: dict[str, tuple[float, float]] = {}
        for t in req.targets:
            # Fit a per-property GP
            prop_y = []
            for form in req.tested:
                v = next((p["value"] for p in form.get("properties", []) if p["name"] == t["property"]), None)
                if v is not None:
                    prop_y.append(v)

            if len(prop_y) == len(X_raw) and len(prop_y) > 0:
                prop_arr = np.array(prop_y)
                prop_scaler = Scaler().fit(prop_arr.reshape(-1, 1))
                prop_scaled = prop_scaler.transform(prop_arr.reshape(-1, 1)).ravel()
                prop_gp = GPModel(n_restarts=2, random_seed=settings.optimizer_random_seed)
                prop_gp.fit(X_scaled, prop_scaled)
                pm, ps = prop_gp.predict(cand.ingredients_scaled.reshape(1, -1))
                # Unscale
                pm_raw = prop_scaler.inverse_transform(pm.reshape(-1, 1)).ravel()[0]
                ps_raw = float(ps[0]) * float((prop_scaler.max_ - prop_scaler.min_)[0] or 1.0)
                prop_predictions[t["property"]] = (pm_raw, ps_raw)
            else:
                prop_predictions[t["property"]] = (0.0, 0.0)

        raw_candidates.append({
            "label": f"P-{req.iteration_n}-{i + 1}",
            "ing_amounts": {n: float(round(v, 2)) for n, v in zip(ing_names, ing_amounts_raw, strict=True)},
            "prop_predictions": prop_predictions,
            "acq_value": cand.acq_value,
        })

    # --- Ask LLM for rationale only ---
    rationales = _get_rationales(req, raw_candidates, target_names)

    results: list[ProposedFormulation] = []
    for rc, rationale in zip(raw_candidates, rationales, strict=True):
        predictions = [
            {"property": prop, "value": vals[0], "sigma": vals[1]}
            for prop, vals in rc["prop_predictions"].items()
        ]
        results.append(ProposedFormulation(
            label=rc["label"],
            rationale=rationale,
            ingredients=rc["ing_amounts"],
            predictions=predictions,
        ))

    return results


_RATIONALE_PROMPT = """\
You are a chemistry DOE expert reviewing AI-proposed formulations for {project_name} (Iteration {iteration_n}).

A Gaussian Process Bayesian optimizer selected these candidates. For each one, write a single concise sentence \
explaining the chemical reasoning for why this composition is promising given the targets and what the data shows so far.

Targets: {targets}

Candidates:
{candidates}

Respond with ONLY valid JSON — an array of strings, one rationale per candidate in the same order:
["rationale for candidate 1", "rationale for candidate 2", ...]
"""


def _get_rationales(req: ProposalRequest, raw_candidates: list[dict], target_names: list[str]) -> list[str]:
    cand_lines = []
    for rc in raw_candidates:
        ing_str = ", ".join(f"{k}={v}g" for k, v in rc["ing_amounts"].items())
        prop_str = ", ".join(
            f"{p}={vals[0]:.3g}±{vals[1]:.3g}"
            for p, vals in rc["prop_predictions"].items()
        )
        cand_lines.append(f"- {rc['label']}: [{ing_str}] → predicted [{prop_str}]")

    targets_str = ", ".join(
        f"{t['property']} {t['goal']}" for t in req.targets
    )

    prompt = _RATIONALE_PROMPT.format(
        project_name=req.project_name,
        iteration_n=req.iteration_n,
        targets=targets_str,
        candidates="\n".join(cand_lines),
    )

    api_key = settings.anthropic_api_key
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    rationales = json.loads(raw)
    if isinstance(rationales, list) and len(rationales) == len(raw_candidates):
        return rationales
    return ["GP-selected candidate." for _ in raw_candidates]
