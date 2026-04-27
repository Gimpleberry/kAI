"""
CBC choice task generator.

Generates a set of choice tasks where each task contains N alternatives,
and each alternative is a bundle of one level per attribute.

Design quality matters enormously — a poor design gives unidentifiable
or biased part-worth estimates regardless of how many tasks you collect.

DETERMINISM CONTRACT (per ADR-005):
    Given identical (taxonomy, n_tasks, n_alts_per_task, method, seed),
    this function MUST produce byte-identical output across runs and across
    Python versions >= 3.12. We rely on this for design reproducibility:
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
      general-purpose choice for CBC. (Implemented in v1.1 as level-balanced
      random assignment; within-task overlap minimization is deferred until
      Phase 1.2 diagnostics tell us whether D-efficiency requires it.)
    - "orthogonal": Pure orthogonal arrays via pyDOE3. Cleaner math but
      can produce dominated alternatives (one obviously beats another).
      Not implemented in v1.1.
    - "random": Pure random sampling. Baseline; never use in production.
      Not implemented in v1.1.

The output is a structure that the elicitation API can serve and the
estimation engine can consume, with no logic between them.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Per Tenet 1: GENERATOR_VERSION lives in shared.py. We import it as a
# convenience alias here for callers that already import from this module.
from kai.shared import CBC_GENERATOR_VERSION as GENERATOR_VERSION  # noqa: F401
from kai.taxonomy.schema import Taxonomy

# Methods recognized by this module. Only "balanced_overlap" is implemented
# in Phase 1.1; the others raise NotImplementedError to make the surface
# discoverable without lying about capabilities.
_KNOWN_METHODS: frozenset[str] = frozenset({"balanced_overlap", "orthogonal", "random"})
_IMPLEMENTED_METHODS: frozenset[str] = frozenset({"balanced_overlap"})


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

    Args:
        taxonomy: Validated Taxonomy whose attributes/levels populate the
            design. The taxonomy_version is the caller's responsibility to
            track alongside the seed (per ADR-005).
        n_tasks: Number of choice tasks shown to the respondent. Must be >= 1.
        n_alts_per_task: Number of alternatives per task. Must be >= 2.
        method: Design generation method. Only "balanced_overlap" is
            implemented in v1.1; "orthogonal" and "random" raise
            NotImplementedError. Unknown methods raise ValueError.
        seed: RNG seed. Determines the design uniquely given the other
            arguments (see DETERMINISM CONTRACT in module docstring).

    Returns:
        CBCDesign with `d_efficiency=None`. The diagnostics module
        (Phase 1.2) is responsible for computing D-efficiency and
        returning a separate report; the generator does not self-evaluate.

    Raises:
        ValueError: For invalid method or out-of-range n_tasks/n_alts_per_task.
        NotImplementedError: For "orthogonal" / "random" methods (Phase 2+).

    Algorithm (balanced_overlap, v1.1):
        For each attribute (iterated in id-sorted order):
          1. Build a sequence of length n_tasks * n_alts_per_task where each
             level appears floor(n_slots / n_levels) times. The remainder
             slots (n_slots mod n_levels) are distributed to the levels
             whose ids sort first alphabetically — fully deterministic.
          2. Shuffle that sequence with a single seeded numpy Generator,
             consumed in attribute-sort order.
          3. Reshape to (n_tasks, n_alts_per_task) for assignment.

        This guarantees PERFECT level balance per attribute (or near-perfect
        when n_slots is not divisible by n_levels: max deviation is one slot,
        well below the 15% imbalance gate). Within-task overlap between
        alternatives is uncontrolled in v1.1 — it falls out of the
        independent shuffles. If Phase 1.2 diagnostics show this hurts
        D-efficiency below the 0.85 gate, a swap-based overlap-minimization
        pass will be added in a follow-up, gated on a measured need.
    """
    # ---- Argument validation (loud failures, per Tenet 5) -----------------
    if method not in _KNOWN_METHODS:
        raise ValueError(f"Unknown method: {method!r}. " f"Known methods: {sorted(_KNOWN_METHODS)}")
    if method not in _IMPLEMENTED_METHODS:
        raise NotImplementedError(
            f"method={method!r} is recognized but not implemented in v1.1. "
            f"Currently implemented: {sorted(_IMPLEMENTED_METHODS)}"
        )
    if n_tasks < 1:
        raise ValueError(f"n_tasks must be >= 1, got {n_tasks}")
    if n_alts_per_task < 2:
        raise ValueError(
            f"n_alts_per_task must be >= 2 (CBC requires contrast), " f"got {n_alts_per_task}"
        )

    # ---- Deterministic setup ----------------------------------------------
    # Single RNG instance, consumed in deterministic order. We use
    # numpy.random.default_rng (PCG64), whose stream is stable across
    # numpy 2.x at the same seed.
    rng = np.random.default_rng(seed)
    n_slots = n_tasks * n_alts_per_task

    # Sort attributes by id — belt-and-suspenders against any future
    # change in Pydantic that might affect iteration order of the
    # validated model.
    sorted_attrs = sorted(taxonomy.attributes, key=lambda a: a.id)

    # ---- Per-attribute level-balanced shuffle -----------------------------
    # assignments[attr.id] is a (n_tasks, n_alts_per_task) array of level ids.
    assignments: dict[str, np.ndarray] = {}
    for attr in sorted_attrs:
        sorted_level_ids = sorted(lvl.id for lvl in attr.levels)
        n_levels = len(sorted_level_ids)

        # Each level appears `base` times; the first `rem` levels (in
        # alphabetical id order) get one extra. This is deterministic.
        base, rem = divmod(n_slots, n_levels)
        counts = [base + (1 if i < rem else 0) for i in range(n_levels)]

        # Build the flat sequence in deterministic order, then shuffle.
        # Using object dtype to avoid numpy fixed-width string truncation.
        sequence = np.array(
            [
                level_id
                for level_id, count in zip(sorted_level_ids, counts, strict=True)
                for _ in range(count)
            ],
            dtype=object,
        )
        rng.shuffle(sequence)

        assignments[attr.id] = sequence.reshape(n_tasks, n_alts_per_task)

    # ---- Build the immutable output structure -----------------------------
    tasks: list[ChoiceTask] = []
    for task_idx in range(n_tasks):
        alternatives: list[Alternative] = []
        for alt_idx in range(n_alts_per_task):
            # dict literal in sorted-attr-id order — gives stable insertion
            # order and therefore stable pickle output (Python 3.7+ dicts).
            levels = {
                attr.id: str(assignments[attr.id][task_idx, alt_idx]) for attr in sorted_attrs
            }
            alternatives.append(Alternative(levels=levels))
        tasks.append(ChoiceTask(task_id=task_idx, alternatives=alternatives))

    return CBCDesign(
        tasks=tasks,
        method=method,
        seed=seed,
        d_efficiency=None,  # Filled by diagnose_cbc_design() in Phase 1.2
    )
