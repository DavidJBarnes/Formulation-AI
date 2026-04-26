"""Unit tests for the Bayesian optimizer module."""

from __future__ import annotations

import numpy as np
import pytest

from formulation_ai.optimizer.acquisition import (
    evaluate,
    expected_improvement,
    probability_of_improvement,
    upper_confidence_bound,
)
from formulation_ai.optimizer.candidate_selector import select_candidates
from formulation_ai.optimizer.gp_model import GPModel
from formulation_ai.optimizer.scaler import Scaler

# ---------------------------------------------------------------------------
# Scaler
# ---------------------------------------------------------------------------

def test_scaler_fit_transform_roundtrip():
    X = np.array([[1.0, 10.0], [2.0, 20.0], [3.0, 30.0]])
    s = Scaler()
    X_scaled = s.fit_transform(X)
    assert X_scaled.min() == pytest.approx(0.0)
    assert X_scaled.max() == pytest.approx(1.0)
    X_back = s.inverse_transform(X_scaled)
    np.testing.assert_allclose(X_back, X, atol=1e-9)


def test_scaler_constant_column():
    X = np.array([[5.0, 1.0], [5.0, 2.0], [5.0, 3.0]])
    s = Scaler()
    X_scaled = s.fit_transform(X)
    # Constant column should stay at 0, not blow up
    assert np.all(np.isfinite(X_scaled))
    assert np.all(X_scaled[:, 0] == 0.0)


# ---------------------------------------------------------------------------
# Acquisition functions
# ---------------------------------------------------------------------------

def test_ei_improves_over_best():
    mean = np.array([1.5, 2.0, 0.5])
    std = np.array([0.1, 0.1, 0.1])
    y_best = 1.0
    ei = expected_improvement(mean, std, y_best)
    # Point above y_best should have higher EI
    assert ei[1] > ei[0] > ei[2]


def test_ucb_higher_std_wins():
    mean = np.array([1.0, 1.0])
    std = np.array([0.5, 2.0])
    ucb = upper_confidence_bound(mean, std, kappa=2.0)
    assert ucb[1] > ucb[0]


def test_pi_returns_probability():
    mean = np.array([1.5])
    std = np.array([0.1])
    pi = probability_of_improvement(mean, std, y_best=1.0)
    assert 0.0 <= float(pi[0]) <= 1.0


def test_evaluate_dispatches():
    mean = np.array([1.0])
    std = np.array([0.5])
    assert evaluate("ei", mean, std, 0.5).shape == (1,)
    assert evaluate("ucb", mean, std, 0.5).shape == (1,)
    assert evaluate("pi", mean, std, 0.5).shape == (1,)


# ---------------------------------------------------------------------------
# GP model
# ---------------------------------------------------------------------------

def _make_toy_data(n: int = 10, d: int = 3, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    X = rng.uniform(0, 1, (n, d))
    y = np.sin(X[:, 0] * 3) + X[:, 1] * 2 + rng.normal(0, 0.1, n)
    return X, y


def test_gp_fit_and_predict():
    X, y = _make_toy_data()
    gp = GPModel(n_restarts=1, random_seed=42)
    gp.fit(X, y)
    mean, std = gp.predict(X)
    assert mean.shape == (len(X),)
    assert std.shape == (len(X),)
    assert np.all(std >= 0)


def test_gp_uncertainty_higher_away_from_data():
    X_train = np.array([[0.1], [0.9]])
    y_train = np.array([0.0, 1.0])
    gp = GPModel(n_restarts=1, random_seed=0)
    gp.fit(X_train, y_train)
    # Middle of training range vs far extrapolation
    _, std_mid = gp.predict(np.array([[0.5]]))
    _, std_far = gp.predict(np.array([[5.0]]))
    assert float(std_far[0]) >= float(std_mid[0])


# ---------------------------------------------------------------------------
# Candidate selector
# ---------------------------------------------------------------------------

def test_select_candidates_returns_requested_count():
    X, y = _make_toy_data(n=8, d=2, seed=1)
    scaler = Scaler().fit(X)
    X_scaled = scaler.transform(X)
    y_scaler = Scaler().fit(y.reshape(-1, 1))
    y_scaled = y_scaler.transform(y.reshape(-1, 1)).ravel()

    gp = GPModel(n_restarts=1, random_seed=42)
    gp.fit(X_scaled, y_scaled)

    candidates = select_candidates(
        gp=gp,
        x_scaler=scaler,
        n_ingredients=2,
        n_candidates=3,
        y_best=float(y_scaled.max()),
        bounds_scaled=[(0.0, 1.0), (0.0, 1.0)],
        random_seed=42,
    )
    assert len(candidates) == 3


def test_select_candidates_respects_bounds():
    X, y = _make_toy_data(n=8, d=2, seed=2)
    scaler = Scaler().fit(X)
    X_scaled = scaler.transform(X)
    y_scaler = Scaler().fit(y.reshape(-1, 1))
    y_scaled = y_scaler.transform(y.reshape(-1, 1)).ravel()

    gp = GPModel(n_restarts=1, random_seed=0)
    gp.fit(X_scaled, y_scaled)

    bounds = [(0.2, 0.8), (0.3, 0.7)]
    candidates = select_candidates(
        gp=gp,
        x_scaler=scaler,
        n_ingredients=2,
        n_candidates=2,
        y_best=float(y_scaled.max()),
        bounds_scaled=bounds,
        random_seed=0,
    )
    for c in candidates:
        for i, (lo, hi) in enumerate(bounds):
            assert lo - 1e-6 <= c.ingredients_scaled[i] <= hi + 1e-6


# ---------------------------------------------------------------------------
# Dispatcher fallback
# ---------------------------------------------------------------------------

def test_llm_fallback_when_below_threshold(monkeypatch):
    """proposal_engine.run_proposal uses LLM when tested < min_observations."""
    from formulation_ai.services import proposal_engine
    from formulation_ai.services.proposal_engine import ProposalRequest, ProposedFormulation

    called_llm = []

    def fake_llm(req):
        called_llm.append(True)
        return [ProposedFormulation("P-1-1", "test", {}, [])]

    monkeypatch.setattr(proposal_engine, "_run_llm_proposal", fake_llm)
    monkeypatch.setattr("formulation_ai.config.settings.optimizer_backend", "gp_sklearn")
    monkeypatch.setattr("formulation_ai.config.settings.optimizer_min_observations", 3)

    req = ProposalRequest(
        project_name="Test",
        iteration_n=1,
        ingredients=[],
        targets=[],
        base_products=[],
        tested=[],  # 0 < 3 → fallback to LLM
    )
    proposal_engine.run_proposal(req)
    assert called_llm, "Expected LLM fallback when tested count is below threshold"
