"""Gaussian Process surrogate model wrapping scikit-learn."""

from __future__ import annotations

import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel


class GPModel:
    """
    Single-output GP surrogate (Matérn 2.5 kernel).

    Inputs are assumed to be already scaled to [0, 1].
    Outputs are the scalarized target score (higher = better).
    """

    def __init__(self, n_restarts: int = 5, random_seed: int | None = None) -> None:
        kernel = Matern(nu=2.5) + WhiteKernel(noise_level=1e-3, noise_level_bounds=(1e-5, 1e-1))
        self.gp = GaussianProcessRegressor(
            kernel=kernel,
            n_restarts_optimizer=n_restarts,
            normalize_y=True,
            random_state=random_seed,
        )
        self._fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> GPModel:
        self.gp.fit(X, y)
        self._fitted = True
        return self

    def predict(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return (mean, std) arrays."""
        mean, std = self.gp.predict(X, return_std=True)
        return mean, std

    @property
    def is_fitted(self) -> bool:
        return self._fitted
