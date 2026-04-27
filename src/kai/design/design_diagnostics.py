"""
Design diagnostics — quality metrics on generated experimental designs.

Run AFTER design generation to verify the design will actually let us
estimate unbiased part-worths. Better to fail here than after collecting
data on a degenerate design.

Metrics:
    - D-efficiency: how close to optimal information matrix
    - Level balance: each level appears with similar frequency
    - Pair balance: each level pair co-occurs with similar frequency
    - Dominated alternatives: alternatives that strictly dominate others
      (these should be rare; they leak no preference information)
"""

from __future__ import annotations

from dataclasses import dataclass

from kai.design.cbc_generator import CBCDesign
from kai.taxonomy.schema import Taxonomy


@dataclass(frozen=True)
class DesignReport:
    """Quality assessment of a CBC design."""

    d_efficiency: float
    level_balance: dict[str, dict[str, float]]  # attr -> level -> frequency
    max_level_imbalance: float
    n_dominated_alternatives: int
    passes_gates: bool
    failed_gates: list[str]


def diagnose_cbc_design(
    design: CBCDesign,
    taxonomy: Taxonomy,
    min_d_efficiency: float = 0.85,
    max_level_imbalance: float = 0.15,
) -> DesignReport:
    """Compute design quality metrics and check against gates.

    NOT YET IMPLEMENTED — scaffolding stub.
    """
    raise NotImplementedError("Design diagnostics pending")
