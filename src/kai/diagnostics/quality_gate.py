"""
Quality gate — combines diagnostics into a single pass/fail decision.

Aligned with tenet #5 (QC over backtracking): a profile that fails quality
gates is NOT exported as the canonical result. The user is told what failed
and what additional data would fix it.

Default gate criteria:
    - Convergence: must converge
    - Consistency: fit_consistency >= 0.75, transitivity_violations <= 5%
    - Stability: split-half correlation >= 0.8
    - Coverage: every attribute has at least one CI fully separated from zero
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QualityGateResult:
    passed: bool
    failures: list[str]
    recommendations: list[str]


def evaluate_quality_gate(
    consistency_report: object,
    convergence_report: object,
    stability_report: object,
) -> QualityGateResult:
    """Combine diagnostic reports into pass/fail. NOT YET IMPLEMENTED."""
    raise NotImplementedError
