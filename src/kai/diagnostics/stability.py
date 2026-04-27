"""
Stability diagnostics — how robust are the estimates?

Tests the profile against perturbation:
    - Bootstrap: resample observations, re-estimate, look at part-worth variance
    - Leave-one-out: drop each task, re-estimate, look at sensitivity
    - Subset estimation: do estimates from first half match second half?
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StabilityReport:
    bootstrap_cis: dict[str, tuple[float, float]]
    max_loo_sensitivity: float
    split_half_correlation: float
    is_stable: bool


def assess_stability(observations: list, estimator: object) -> StabilityReport:
    """Run stability checks. NOT YET IMPLEMENTED."""
    raise NotImplementedError
