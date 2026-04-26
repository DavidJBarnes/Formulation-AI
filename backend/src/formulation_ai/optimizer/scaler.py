"""Min-max scaling for ingredient amounts and target properties."""

from __future__ import annotations

import numpy as np


class Scaler:
    def __init__(self) -> None:
        self.min_: np.ndarray | None = None
        self.max_: np.ndarray | None = None

    def fit(self, X: np.ndarray) -> Scaler:
        self.min_ = X.min(axis=0)
        self.max_ = X.max(axis=0)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        assert self.min_ is not None
        span = self.max_ - self.min_
        span[span == 0] = 1.0  # constant columns stay at 0
        return (X - self.min_) / span

    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        assert self.min_ is not None
        span = self.max_ - self.min_
        span[span == 0] = 1.0
        return X * span + self.min_

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)
