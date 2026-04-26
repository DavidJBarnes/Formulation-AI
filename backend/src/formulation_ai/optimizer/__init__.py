"""Bayesian optimizer (Phase 2). Entry point: run_gp_proposal()."""

from formulation_ai.optimizer.candidate_selector import select_candidates
from formulation_ai.optimizer.gp_model import GPModel

__all__ = ["GPModel", "select_candidates"]
