"""Formulation proposal engine — dispatches to LLM or GP backend."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import anthropic
from openai import OpenAI

from formulation_ai.config import get_llm_config, settings


@dataclass
class ProposedFormulation:
    label: str
    rationale: str
    ingredients: dict[str, float]
    predictions: list[dict]  # [{property, value, sigma}]


@dataclass
class ProposalRequest:
    project_name: str
    iteration_n: int
    ingredients: list[dict]    # [{name, unit, min, max}]
    targets: list[dict]        # [{property, unit, goal, reference, weight}]
    base_products: list[dict]  # [{label, ingredients, properties}]
    tested: list[dict]         # [{label, iteration, ingredients, properties}]
    n_candidates: int = 3
    batch_total_g: float | None = None


def run_proposal(
    req: ProposalRequest,
    db_session=None,
) -> list[ProposedFormulation]:
    """Dispatch to GP or LLM backend based on settings and available data."""
    use_gp = (
        settings.optimizer_backend == "gp_sklearn"
        and len(req.tested) >= settings.optimizer_min_observations
    )
    if use_gp:
        from formulation_ai.optimizer.gp_proposal import run_gp_proposal
        return run_gp_proposal(req)
    return _run_llm_proposal(req, db_session=db_session)


# ---------------------------------------------------------------------------
# LLM-only backend (Phase 1)
# ---------------------------------------------------------------------------

_SYSTEM = """\
You are a chemistry formulation DOE expert. \
Given existing base products and any tested results so far, propose new candidate formulations \
that are most likely to meet the targets. \
Be specific about amounts and honest about prediction uncertainty (1-sigma). \
Think carefully about what the data implies before proposing."""

_USER_TMPL = """\
## Project: {project_name}  (Iteration {iteration_n})

### Ingredients (use these, stay within stated bounds where given)
{ingredients_block}

### Targets
{targets_block}

### Base products
{base_block}

### Previously tested formulations
{tested_block}

---
Propose exactly {n} new candidate formulations.

Respond with ONLY valid JSON in this exact shape — no markdown, no explanation outside the JSON:
{{
  "candidates": [
    {{
      "label": "P-{iteration_n}-1",
      "rationale": "one or two sentences on why this composition is promising",
      "ingredients": {{"Ingredient Name": numeric_amount, ...}},
      "predictions": [
        {{"property": "Property Name", "value": numeric_value, "sigma": numeric_1sigma}}
      ]
    }}
  ]
}}
"""


def _fmt_ingredients(ingredients: list[dict]) -> str:
    lines = []
    for ing in ingredients:
        bounds = ""
        if ing.get("min") is not None or ing.get("max") is not None:
            lo = ing.get("min", "?")
            hi = ing.get("max", "?")
            bounds = f"  [{lo}–{hi} {ing['unit']}]"
        lines.append(f"- {ing['name']} ({ing['unit']}){bounds}")
    return "\n".join(lines) or "(none)"


def _fmt_targets(targets: list[dict]) -> str:
    lines = []
    for t in targets:
        ref = f", relative to {t['reference']}" if t.get("reference") else ""
        lines.append(f"- {t['property']} ({t['unit']}): goal {t['goal']}{ref}")
    return "\n".join(lines) or "(none)"


def _fmt_formulations(formulations: list[dict], label: str) -> str:
    if not formulations:
        return f"*No {label} yet.*"
    rows = []
    for f in formulations:
        ing_str = ", ".join(f"{k}={v}" for k, v in f["ingredients"].items())
        prop_str = ", ".join(
            f"{p['name']}={p['value']}" + (f"±{p['sigma']}" if p.get("sigma") else "")
            for p in f["properties"]
        )
        rows.append(f"- **{f['label']}**: [{ing_str}] → [{prop_str}]")
    return "\n".join(rows)


def _run_llm_proposal(
    req: ProposalRequest,
    db_session=None,
) -> list[ProposedFormulation]:
    """Dispatch to the configured LLM provider."""
    provider, api_key, model = get_llm_config(db_session)

    if api_key is None:
        raise RuntimeError(
            f"No API key configured for provider '{provider}'. "
            "Set FA_LLM_API_KEY or configure via Settings."
        )

    if provider == "deepseek":
        return _run_deepseek_proposal(req, api_key, model)

    # Default: Anthropic
    return _run_anthropic_proposal(req, api_key, model)


def _run_anthropic_proposal(
    req: ProposalRequest,
    api_key: str | None,
    model: str,
) -> list[ProposedFormulation]:
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    prompt = _USER_TMPL.format(
        project_name=req.project_name,
        iteration_n=req.iteration_n,
        ingredients_block=_fmt_ingredients(req.ingredients),
        targets_block=_fmt_targets(req.targets),
        base_block=_fmt_formulations(req.base_products, "base products"),
        tested_block=_fmt_formulations(req.tested, "tested formulations"),
        n=req.n_candidates,
    )

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    data = json.loads(raw)
    return [
        ProposedFormulation(
            label=c["label"],
            rationale=c.get("rationale", ""),
            ingredients=c["ingredients"],
            predictions=c["predictions"],
        )
        for c in data["candidates"]
    ]


def _run_deepseek_proposal(
    req: ProposalRequest,
    api_key: str,
    model: str,
) -> list[ProposedFormulation]:
    """Generate proposals using DeepSeek (OpenAI-compatible API)."""
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

    prompt = _USER_TMPL.format(
        project_name=req.project_name,
        iteration_n=req.iteration_n,
        ingredients_block=_fmt_ingredients(req.ingredients),
        targets_block=_fmt_targets(req.targets),
        base_block=_fmt_formulations(req.base_products, "base products"),
        tested_block=_fmt_formulations(req.tested, "tested formulations"),
        n=req.n_candidates,
    )

    response = client.chat.completions.create(
        model=model,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    data = json.loads(raw)
    return [
        ProposedFormulation(
            label=c["label"],
            rationale=c.get("rationale", ""),
            ingredients=c["ingredients"],
            predictions=c["predictions"],
        )
        for c in data["candidates"]
    ]
