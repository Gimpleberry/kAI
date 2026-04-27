"""
Choice consistency diagnostics.

Detects respondent inconsistency — choices that contradict each other
(e.g., "I prefer A over B" and "I prefer B over A"). Some inconsistency
is normal; lots of it means the respondent was rushing or distracted,
and the estimation will be unreliable.

Metrics:
    - Test-retest reliability (if any tasks are repeated, do they match?)
    - Transitivity violations (A>B, B>C, but C>A)
    - Choice consistency vs. fitted MNL (% of choices the model predicts)
    - Speedrun detection (choices made suspiciously fast)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConsistencyReport:
    """Respondent quality assessment."""

    n_observations: int
    test_retest_match_rate: float | None
    transitivity_violations: int
    fit_consistency: float  # % of choices the fitted model gets right
    speedrun_detected: bool
    overall_quality: str  # "high" | "medium" | "low"


def assess_consistency(observations: list, fitted_model: object) -> ConsistencyReport:
    """Compute respondent consistency metrics.

    NOT YET IMPLEMENTED.
    """
    raise NotImplementedError("Consistency diagnostics pending")
