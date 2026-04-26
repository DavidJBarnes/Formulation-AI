"""Acquisition functions: EI, UCB, PI."""

from __future__ import annotations

import numpy as np
from scipy.stats import norm


def expected_improvement(mean: np.ndarray, std: np.ndarray, y_best: float, xi: float = 0.01) -> np.ndarray:
    z = (mean - y_best - xi) / (std + 1e-9)
    return (mean - y_best - xi) * norm.cdf(z) + std * norm.pdf(z)


def upper_confidence_bound(mean: np.ndarray, std: np.ndarray, kappa: float = 2.0) -> np.ndarray:
    return mean + kappa * std


def probability_of_improvement(mean: np.ndarray, std: np.ndarray, y_best: float, xi: float = 0.01) -> np.ndarray:
    z = (mean - y_best - xi) / (std + 1e-9)
    return norm.cdf(z)


def evaluate(
    acq: str,
    mean: np.ndarray,
    std: np.ndarray,
    y_best: float,
    kappa: float = 2.0,
    xi: float = 0.01,
) -> np.ndarray:
    if acq == "ucb":
        return upper_confidence_bound(mean, std, kappa)
    if acq == "pi":
        return probability_of_improvement(mean, std, y_best, xi)
    return expected_improvement(mean, std, y_best, xi)
