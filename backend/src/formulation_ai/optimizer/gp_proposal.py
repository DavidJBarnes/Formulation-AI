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

# ---------------------------------------------------------------------------
# Goal-aware property scoring
# ---------------------------------------------------------------------------

def _reference_value(prop_name: str, reference: str | None, base_products: list[dict]) -> float | None:
    """Look up the reference value for a +/-% goal from the base products list."""
    if not reference or reference.lower() in ("absolute", "none", ""):
        return None
    ref_lower = reference.lower()
    if "average" in ref_lower:
        vals = [
            float(p["value"])
            for bp in base_products
            for p in bp.get("properties", [])
            if p["name"] == prop_name and isinstance(p.get("value"), (int, float))
        ]
        return sum(vals) / len(vals) if vals else None
    for bp in base_products:
        if bp["label"] == reference:
            for p in bp.get("properties", []):
                if p["name"] == prop_name and isinstance(p.get("value"), (int, float)):
                    return float(p["value"])
    return None


def _property_score(value: float, goal: str, ref_value: float | None = None) -> float:
    """
    Normalize a measured property value to a comparable score (higher = better, ~1 = target met).

    All goal types are mapped to the same [0, ∞) scale so the weighted sum the GP
    trains on is commensurable across properties with different units and magnitudes.
    Without this, a 105 KU viscosity reading dominates a 4.5 MPa adhesion reading
    in the raw weighted sum, causing the GP to effectively ignore small-magnitude targets.
    """
    g = re.sub(r"\s", "", goal)

    m = re.match(r"^>=(.+)$", g)
    if m:
        return value / max(float(m.group(1)), 1e-9)

    m = re.match(r"^<=(.+)$", g)
    if m:
        target = float(m.group(1))
        return target / max(value, 1e-9)

    m = re.match(r"^=(.+)$", g)
    if m:
        target = float(m.group(1))
        return max(0.0, 1.0 - abs(value - target) / max(abs(target), 1e-9))

    m = re.match(r"^\+(\d+(?:\.\d+)?)%$", g)
    if m and ref_value is not None:
        target = ref_value * (1 + float(m.group(1)) / 100)
        return value / max(target, 1e-9)

    m = re.match(r"^-(\d+(?:\.\d+)?)%$", g)
    if m and ref_value is not None:
        target = ref_value * (1 - float(m.group(1)) / 100)
        return target / max(value, 1e-9)

    m = re.fullmatch(r"\[(.+),(.+)\]", g)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        if lo <= value <= hi:
            return 1.0
        half = max((hi - lo) / 2, 1e-9)
        dist = min(abs(value - lo), abs(value - hi))
        return max(0.0, 1.0 - dist / half)

    return float(value)  # fallback: no normalization possible


# ---------------------------------------------------------------------------
# Main GP proposal
# ---------------------------------------------------------------------------

def run_gp_proposal(req: ProposalRequest) -> list[ProposedFormulation]:
    """Fit GP on tested data, select candidates via Kriging Believer, ask LLM for rationale."""
    ing_names = [i["name"] for i in req.ingredients]
    weights = [t.get("weight", 1.0) for t in req.targets]
    weight_arr = np.array(weights, dtype=float)
    if weight_arr.sum() > 0:
        weight_arr = weight_arr / weight_arr.sum()

    # Reference values for +/-% goals (looked up from base products once)
    ref_values = {
        t["property"]: _reference_value(t["property"], t.get("reference"), req.base_products)
        for t in req.targets
    }

    # --- Build training data with goal-normalized scores ---
    X_raw: list[list[float]] = []
    y_raw: list[float] = []

    for form in req.tested:
        row = [form["ingredients"].get(n, 0.0) for n in ing_names]
        scores = []
        for t, w in zip(req.targets, weight_arr, strict=True):
            v = next((p["value"] for p in form.get("properties", []) if p["name"] == t["property"]), None)
            if v is not None:
                s = _property_score(float(v), t["goal"], ref_values.get(t["property"]))
                scores.append(s * w)
        if len(scores) == len(req.targets):
            X_raw.append(row)
            y_raw.append(sum(scores))

    X = np.array(X_raw)
    y = np.array(y_raw)

    # --- Fit scaler on DECLARED ingredient bounds, not training data ---
    # Anchoring to declared bounds ensures the GP explores the full feasible space
    # from the first iteration — not just the narrow region already sampled.
    lo_arr = np.array([
        ing.get("min") if ing.get("min") is not None else float(X[:, i].min())
        for i, ing in enumerate(req.ingredients)
    ])
    hi_arr = np.array([
        ing.get("max") if ing.get("max") is not None else float(X[:, i].max())
        for i, ing in enumerate(req.ingredients)
    ])
    hi_arr = np.where(hi_arr > lo_arr, hi_arr, lo_arr + 1.0)  # guard constant ingredients

    x_scaler = Scaler().fit(np.vstack([lo_arr, hi_arr]))
    X_scaled = x_scaler.transform(X)

    # Bounds in scaled space are exactly [0, 1] since scaler is anchored to declared bounds
    bounds_scaled: list[tuple[float, float]] = [(0.0, 1.0)] * len(ing_names)

    # --- Scale y ---
    y_scaler = Scaler().fit(y.reshape(-1, 1))
    y_scaled = y_scaler.transform(y.reshape(-1, 1)).ravel()
    y_best = float(y_scaled.max())

    # --- Batch sum constraint in scaled space ---
    # Raw constraint: sum(x_raw[i]) = batch_total_g
    # In scaled space: x_scaled[i] = (x_raw[i] - lo[i]) / span[i]
    # → sum(x_scaled[i] * span[i]) = batch_total_g - sum(lo[i])
    # → x_scaled @ span = batch_total - sum_lo   (correct linear form)
    span_arr = hi_arr - lo_arr
    span_arr[span_arr == 0] = 1.0
    batch_constraint: tuple[np.ndarray, float] | None = None
    if req.batch_total_g is not None:
        batch_constraint = (span_arr, float(req.batch_total_g) - float(lo_arr.sum()))

    # --- Fit per-property GPs once (used for reporting, not selection) ---
    prop_gps: dict[str, tuple[GPModel, Scaler]] = {}
    for t in req.targets:
        prop_y_vals = [
            float(next((p["value"] for p in form.get("properties", []) if p["name"] == t["property"]), None))  # type: ignore[arg-type]
            for form in req.tested
            if next((p["value"] for p in form.get("properties", []) if p["name"] == t["property"]), None) is not None
        ]
        if len(prop_y_vals) == len(X_raw) and prop_y_vals:
            prop_arr = np.array(prop_y_vals)
            prop_scaler = Scaler().fit(prop_arr.reshape(-1, 1))
            prop_scaled = prop_scaler.transform(prop_arr.reshape(-1, 1)).ravel()
            prop_gp = GPModel(n_restarts=2, random_seed=settings.optimizer_random_seed)
            prop_gp.fit(X_scaled, prop_scaled)
            prop_gps[t["property"]] = (prop_gp, prop_scaler)

    # --- Kriging Believer: select one candidate at a time, refit GP between ---
    # After each candidate is chosen, its GP-predicted mean is added to the training
    # set as a "phantom" observation. The next candidate is selected from a landscape
    # that already "knows" about the previous pick, pushing it to a different region.
    X_aug = X_scaled.copy()
    y_aug = y_scaled.copy()
    candidates = []

    for _ in range(req.n_candidates):
        gp = GPModel(n_restarts=settings.optimizer_n_restarts, random_seed=settings.optimizer_random_seed)
        gp.fit(X_aug, y_aug)

        new_cands = select_candidates(
            gp=gp,
            n_ingredients=len(ing_names),
            n_candidates=1,
            y_best=y_best,
            bounds_scaled=bounds_scaled,
            batch_constraint=batch_constraint,
            acq=settings.optimizer_acquisition,
            kappa=settings.optimizer_ucb_kappa,
            xi=settings.optimizer_ei_xi,
            n_restarts=settings.optimizer_n_restarts,
            random_seed=settings.optimizer_random_seed,
            already_selected=[c.ingredients_scaled for c in candidates],
        )
        if not new_cands:
            break

        cand = new_cands[0]
        candidates.append(cand)
        X_aug = np.vstack([X_aug, cand.ingredients_scaled.reshape(1, -1)])
        y_aug = np.append(y_aug, cand.mean)

    # --- Convert candidates to raw amounts and per-property predictions ---
    raw_candidates = []
    for i, cand in enumerate(candidates):
        ing_amounts_raw = x_scaler.inverse_transform(cand.ingredients_scaled.reshape(1, -1)).ravel()

        prop_predictions: dict[str, tuple[float, float]] = {}
        for t in req.targets:
            if t["property"] in prop_gps:
                prop_gp, prop_scaler = prop_gps[t["property"]]
                pm, ps = prop_gp.predict(cand.ingredients_scaled.reshape(1, -1))
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
    target_names = [t["property"] for t in req.targets]
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
