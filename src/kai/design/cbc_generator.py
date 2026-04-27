"""
CBC choice task generator.

Generates a set of choice tasks where each task contains N alternatives,
and each alternative is a bundle of one level per attribute.

Design quality matters enormously — a poor design gives unidentifiable
or biased part-worth estimates regardless of how many tasks you collect.

DETERMINISM CONTRACT (per ADR-005):
    Given identical (taxonomy, n_tasks, n_alts_per_task, method, seed),
    this function MUST produce byte-identical output across runs and across
    Python versions ≥ 3.12. We rely on this for design reproducibility:
    we store only the seed in the DB and regenerate the design on demand.

    Implementations must:
      - Use only seeded randomness (numpy.random.default_rng(seed))
      - Avoid hash-order dependencies (set/dict iteration order)
      - Avoid time/wallclock-dependent operations
      - Sort all intermediate collections explicitly before sampling

    Tests must verify byte-identical regeneration.

Methods supported:
    - "balanced_overlap": Sawtooth-style; each level appears equally often,
      with controlled overlap between alternatives within a task. Best
      general-purpose choice for CBC.
    - "orthogonal": Pure orthogonal arrays via pyDOE3. Cleaner math but
      can produce dominated alternatives (one obviously beats another).
    - "random": Pure random sampling. Baseline; never use in production.

The output is a structure that the elicitation API can serve and the
estimation engine can consume, with no logic between them.
"""

from __future__ import annotations

from dataclasses import dataclass

# Per Tenet 1: GENERATOR_VERSION lives in shared.py. We import it as a
# convenience alias here for callers that already import from this module.
from kai.shared import CBC_GENERATOR_VERSION as GENERATOR_VERSION  # noqa: F401
from kai.taxonomy.schema import Taxonomy


@dataclass(frozen=True)
class Alternative:
    """One bundle within a choice task — a level for each attribute."""

    levels: dict[str, str]  # attribute_id -> level_id


@dataclass(frozen=True)
class ChoiceTask:
    """A single choice question shown to the respondent."""

    task_id: int
    alternatives: list[Alternative]


@dataclass(frozen=True)
class CBCDesign:
    """Full CBC questionnaire design."""

    tasks: list[ChoiceTask]
    method: str
    seed: int
    d_efficiency: float | None  # Filled by diagnostics


def generate_cbc_design(
    taxonomy: Taxonomy,
    n_tasks: int,
    n_alts_per_task: int,
    method: str = "balanced_overlap",
    seed: int = 42,
) -> CBCDesign:
    """Generate a CBC choice task design.

    NOT YET IMPLEMENTED — returns NotImplementedError stub for scaffolding review.

    Implementation plan:
        1. Generate balanced level frequencies per attribute
        2. Assign levels to alternatives, minimizing within-task duplication
        3. Compute D-efficiency via design matrix determinant
        4. Reject and regenerate if below QUALITY_GATE_MIN_D_EFFICIENCY threshold
    """
    raise NotImplementedError("CBC design generation pending — scaffolding only")
