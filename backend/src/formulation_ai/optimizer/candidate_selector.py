"""
Select next candidate formulations by optimizing the acquisition function
over the ingredient space via random multi-start quasi-Newton search.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from formulation_ai.optimizer.acquisition import evaluate
from formulation_ai.optimizer.gp_model import GPModel
from formulation_ai.optimizer.scaler import Scaler


@dataclass
class Candidate:
    ingredients_scaled: np.ndarray   # shape (n_ingredients,) in [0,1]
    mean: float
    sigma: float
    acq_value: float


def select_candidates(
    gp: GPModel,
    x_scaler: Scaler,
    n_ingredients: int,
    n_candidates: int,
    y_best: float,
    bounds_scaled: list[tuple[float, float]],  # per-ingredient (lo, hi) in scaled space
    batch_constraint: float | None = None,      # scaled sum target if batch_total_g set
    acq: str = "ei",
    kappa: float = 2.0,
    xi: float = 0.01,
    n_restarts: int = 5,
    random_seed: int | None = None,
) -> list[Candidate]:
    rng = np.random.default_rng(random_seed)

    def neg_acq(x: np.ndarray) -> float:
        x2d = x.reshape(1, -1)
        mean, std = gp.predict(x2d)
        score = evaluate(acq, mean, std, y_best, kappa=kappa, xi=xi)
        return -float(score[0])

    constraints = []
    if batch_constraint is not None:
        # sum of scaled ingredients should equal the scaled batch total
        constraints.append({
            "type": "eq",
            "fun": lambda x: np.sum(x) - batch_constraint,
        })

    results: list[Candidate] = []
    tried: list[np.ndarray] = []

    attempts = n_candidates * n_restarts
    starts = rng.uniform(0, 1, size=(attempts, n_ingredients))

    for x0 in starts:
        # Clip to bounds
        x0 = np.clip(x0, [b[0] for b in bounds_scaled], [b[1] for b in bounds_scaled])
        res = minimize(
            neg_acq,
            x0,
            method="SLSQP",
            bounds=bounds_scaled,
            constraints=constraints,
            options={"maxiter": 200, "ftol": 1e-6},
        )
        if not res.success:
            continue
        x_opt = res.x

        # Deduplicate: skip if too close to an already-chosen point
        if any(np.linalg.norm(x_opt - t) < 0.05 for t in tried):
            continue

        mean, std = gp.predict(x_opt.reshape(1, -1))
        results.append(Candidate(
            ingredients_scaled=x_opt,
            mean=float(mean[0]),
            sigma=float(std[0]),
            acq_value=-res.fun,
        ))
        tried.append(x_opt)

        if len(results) >= n_candidates:
            break

    # If optimizer found fewer than needed, fill with best random points
    if len(results) < n_candidates:
        random_X = rng.uniform(0, 1, size=(500, n_ingredients))
        random_X = np.clip(random_X, [b[0] for b in bounds_scaled], [b[1] for b in bounds_scaled])
        mean_r, std_r = gp.predict(random_X)
        scores = evaluate(acq, mean_r, std_r, y_best, kappa=kappa, xi=xi)
        order = np.argsort(-scores)
        for idx in order:
            x_opt = random_X[idx]
            if any(np.linalg.norm(x_opt - t) < 0.05 for t in tried):
                continue
            mean, std = gp.predict(x_opt.reshape(1, -1))
            results.append(Candidate(
                ingredients_scaled=x_opt,
                mean=float(mean[0]),
                sigma=float(std[0]),
                acq_value=float(scores[idx]),
            ))
            tried.append(x_opt)
            if len(results) >= n_candidates:
                break

    return results
