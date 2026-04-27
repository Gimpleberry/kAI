"""
Convergence diagnostics — did the optimizer actually find the optimum?

For MNL: optimizer convergence flag, gradient norm at solution.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConvergenceReport:
    converged: bool
    metric_values: dict[str, float]
    warnings: list[str]


def assess_mnl_convergence(optimizer_result: object) -> ConvergenceReport:
    """Check MNL optimizer converged. NOT YET IMPLEMENTED."""
    raise NotImplementedError
