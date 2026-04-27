"""
MaxDiff (best-worst scaling) estimator.

Each best/worst response gives two pieces of info:
    - Best item beats all other shown items
    - Worst item is beaten by all other shown items

Implements rank-ordered logit on the implied pairwise comparisons.

Output: utility per tenet, used as a prior or anchor for the CBC-derived
importances. Helps when CBC alone leaves some tenets with wide CIs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaxDiffObservation:
    """One best/worst response."""

    task_id: int
    items_shown: list[str]
    best_item: str
    worst_item: str


@dataclass(frozen=True)
class MaxDiffUtilities:
    """Estimated utility per item (tenet)."""

    utilities: dict[str, float]  # tenet_id -> utility
    standard_errors: dict[str, float]


def estimate_maxdiff(
    observations: list[MaxDiffObservation],
) -> MaxDiffUtilities:
    """Estimate item utilities via rank-ordered logit on best/worst pairs.

    NOT YET IMPLEMENTED.
    """
    raise NotImplementedError("MaxDiff estimation pending")
