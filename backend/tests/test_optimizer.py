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
from formulation_ai.optimizer.gp_proposal import _property_score, _reference_value
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
    assert np.all(np.isfinite(X_scaled))
    assert np.all(X_scaled[:, 0] == 0.0)


def test_scaler_fit_on_bounds_maps_extremes_to_zero_one():
    lo = np.array([10.0, 100.0])
    hi = np.array([20.0, 200.0])
    s = Scaler().fit(np.vstack([lo, hi]))
    scaled_lo = s.transform(lo.reshape(1, -1))
    scaled_hi = s.transform(hi.reshape(1, -1))
    np.testing.assert_allclose(scaled_lo, [[0.0, 0.0]], atol=1e-9)
    np.testing.assert_allclose(scaled_hi, [[1.0, 1.0]], atol=1e-9)


# ---------------------------------------------------------------------------
# Acquisition functions
# ---------------------------------------------------------------------------

def test_ei_improves_over_best():
    mean = np.array([1.5, 2.0, 0.5])
    std = np.array([0.1, 0.1, 0.1])
    y_best = 1.0
    ei = expected_improvement(mean, std, y_best)
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
# Goal-normalized property scoring
# ---------------------------------------------------------------------------

def test_property_score_gte_at_target():
    # At exactly the target, score should be 1.0
    assert _property_score(55.0, ">=55") == pytest.approx(1.0)


def test_property_score_gte_above_target():
    # Above target is better (score > 1)
    assert _property_score(60.0, ">=55") > 1.0


def test_property_score_gte_below_target():
    # Below target is worse (score < 1)
    assert _property_score(40.0, ">=55") < 1.0


def test_property_score_lte_at_target():
    assert _property_score(35.0, "<=35") == pytest.approx(1.0)


def test_property_score_lte_above_is_worse():
    assert _property_score(50.0, "<=35") < 1.0


def test_property_score_exact_at_target():
    assert _property_score(105.0, "=105") == pytest.approx(1.0)


def test_property_score_exact_penalizes_deviation():
    score_near = _property_score(106.0, "=105")
    score_far = _property_score(120.0, "=105")
    assert 1.0 > score_near > score_far >= 0.0


def test_property_score_range_inside():
    assert _property_score(140.0, "[100,180]") == pytest.approx(1.0)


def test_property_score_range_outside_penalized():
    score_in = _property_score(140.0, "[100,180]")
    score_out = _property_score(90.0, "[100,180]")
    assert score_in > score_out


def test_property_score_pct_increase_with_ref():
    # +10% of 100 = 110; at 110 score should be 1.0
    assert _property_score(110.0, "+10%", ref_value=100.0) == pytest.approx(1.0)
    assert _property_score(120.0, "+10%", ref_value=100.0) > 1.0
    assert _property_score(100.0, "+10%", ref_value=100.0) < 1.0


def test_property_score_commensurable():
    # A 105 KU viscosity (=105) and a 4.5 MPa adhesion (>=4.5) at target both score ~1.0
    score_visc = _property_score(105.0, "=105")
    score_adh = _property_score(4.5, ">=4.5")
    assert score_visc == pytest.approx(1.0)
    assert score_adh == pytest.approx(1.0)


def test_reference_value_named_product():
    base = [{"label": "Base A", "properties": [{"name": "Tensile", "value": 48.0}]}]
    assert _reference_value("Tensile", "Base A", base) == pytest.approx(48.0)


def test_reference_value_average():
    base = [
        {"label": "A", "properties": [{"name": "P", "value": 60.0}]},
        {"label": "B", "properties": [{"name": "P", "value": 80.0}]},
    ]
    assert _reference_value("P", "average of base", base) == pytest.approx(70.0)


def test_reference_value_absolute_returns_none():
    assert _reference_value("P", "absolute", []) is None


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
        n_ingredients=2,
        n_candidates=2,
        y_best=float(y_scaled.max()),
        bounds_scaled=bounds,
        random_seed=0,
    )
    for c in candidates:
        for i, (lo, hi) in enumerate(bounds):
            assert lo - 1e-6 <= c.ingredients_scaled[i] <= hi + 1e-6


def test_select_candidates_avoids_already_selected():
    """Kriging Believer: already_selected candidates must not be re-picked."""
    X, y = _make_toy_data(n=10, d=2, seed=3)
    scaler = Scaler().fit(X)
    X_scaled = scaler.transform(X)
    y_scaler = Scaler().fit(y.reshape(-1, 1))
    y_scaled = y_scaler.transform(y.reshape(-1, 1)).ravel()

    gp = GPModel(n_restarts=1, random_seed=0)
    gp.fit(X_scaled, y_scaled)

    c1 = select_candidates(gp=gp, n_ingredients=2, n_candidates=1,
                           y_best=float(y_scaled.max()), bounds_scaled=[(0.0, 1.0)] * 2,
                           random_seed=0)
    assert len(c1) == 1

    c2 = select_candidates(gp=gp, n_ingredients=2, n_candidates=1,
                           y_best=float(y_scaled.max()), bounds_scaled=[(0.0, 1.0)] * 2,
                           random_seed=0, already_selected=[c1[0].ingredients_scaled])
    assert len(c2) == 1
    dist = np.linalg.norm(c1[0].ingredients_scaled - c2[0].ingredients_scaled)
    assert dist >= 0.05, f"Candidates too close: dist={dist:.4f}"


def test_select_candidates_linear_batch_constraint():
    """With batch constraint, optimizer should satisfy x @ coeffs ≈ rhs."""
    X, y = _make_toy_data(n=8, d=2, seed=4)
    scaler = Scaler().fit(X)
    X_scaled = scaler.transform(X)
    y_scaler = Scaler().fit(y.reshape(-1, 1))
    y_scaled = y_scaler.transform(y.reshape(-1, 1)).ravel()

    gp = GPModel(n_restarts=1, random_seed=0)
    gp.fit(X_scaled, y_scaled)

    # coeffs = [1.0, 1.0], rhs = 0.8 → constrained sum
    span = np.array([1.0, 1.0])
    rhs = 0.8
    candidates = select_candidates(
        gp=gp,
        n_ingredients=2,
        n_candidates=1,
        y_best=float(y_scaled.max()),
        bounds_scaled=[(0.0, 1.0), (0.0, 1.0)],
        batch_constraint=(span, rhs),
        random_seed=0,
    )
    if candidates:
        actual = float(np.dot(candidates[0].ingredients_scaled, span))
        assert abs(actual - rhs) < 0.05


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
