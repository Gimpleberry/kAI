"""
Design diagnostics - quality metrics on generated experimental designs.

Run AFTER design generation to verify the design will actually let us
estimate unbiased part-worths. Better to fail here than after collecting
data on a degenerate design.

Metrics:
    - D-efficiency: how close to optimal information matrix (uniform-prior
      approximation; see docstring of `diagnose_cbc_design` for details).
    - Level balance: each level appears with similar frequency across the
      whole design.
    - Duplicate alternatives: alternatives that are identical to another
      alternative WITHIN the same task (these leak no preference info).

Note on "dominance": strict dominance (A is at least as good as B on every
attribute, strictly better on at least one) requires preference direction
metadata not currently in the taxonomy schema. We report duplicates instead,
which is computable and a real pathology. Real dominance detection is
captured as a BACKLOG follow-up.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np

from kai.design.cbc_generator import CBCDesign
from kai.shared import (
    QUALITY_GATE_MAX_LEVEL_IMBALANCE,
    QUALITY_GATE_MIN_D_EFFICIENCY,
)
from kai.taxonomy.schema import Taxonomy


@dataclass(frozen=True)
class DesignReport:
    """Quality assessment of a CBC design.

    Fields:
        d_efficiency: Relative D-efficiency under uniform-prior assumption.
            Range roughly [0, 1]; orthogonal balanced design ~= 1.0.
        level_balance: Per-attribute frequency of each level, expressed as
            a fraction of total slots for that attribute.
            level_balance[attr_id][level_id] = count / n_slots.
        max_level_imbalance: Worst case max(|freq * n_levels - 1|) over all
            (attr, level) pairs. 0.0 means every level appears exactly the
            uniform expected count; 1.0 means a level is missing entirely
            or appears at twice its expected rate.
        n_duplicate_alternatives: Total count of alternatives that share
            their full level vector with at least one other alternative
            in the SAME task. (See module docstring on why this is
            duplicates-not-dominance.)
        passes_gates: True iff d_efficiency and max_level_imbalance both
            satisfy their thresholds. Duplicate count is reported but not
            gated (per Phase 1.2 design decision).
        failed_gates: Human-readable descriptions of any failed gates.
            Empty list iff passes_gates is True.
    """

    d_efficiency: float
    level_balance: dict[str, dict[str, float]]
    max_level_imbalance: float
    n_duplicate_alternatives: int
    passes_gates: bool
    failed_gates: list[str]


def diagnose_cbc_design(
    design: CBCDesign,
    taxonomy: Taxonomy,
    min_d_efficiency: float = QUALITY_GATE_MIN_D_EFFICIENCY,
    max_level_imbalance: float = QUALITY_GATE_MAX_LEVEL_IMBALANCE,
) -> DesignReport:
    """Compute design quality metrics and check against gates.

    Args:
        design: A CBCDesign to evaluate.
        taxonomy: The taxonomy the design was generated against. Caller is
            responsible for matching versions; we don't re-check here.
        min_d_efficiency: Pass threshold for D-efficiency. Defaults to the
            shared cross-module constant.
        max_level_imbalance: Pass threshold for level balance. Defaults to
            the shared cross-module constant.

    Returns:
        DesignReport with all fields populated.

    D-efficiency formulation:
        We use the standard relative D-efficiency for multinomial logit
        under the uniform-prior assumption:

            D-eff = (det(I))^(1/p) / N

        where I is the MNL information matrix:

            I = sum_t (X_t' M X_t)

        with X_t the (J, p) effects-coded submatrix for task t, J the
        number of alternatives per task, and M = I_J - (1/J) * 1 * 1'
        the J x J within-task centering matrix.

        Equivalently: I = X_c' X_c where X_c is the full design matrix
        with each task's rows centered to zero column-means within the
        task. The centering reflects that MNL's likelihood depends on
        differences within a task, not absolute level values. This
        means task-degenerate designs (where an attribute is constant
        across all alternatives in a task) correctly contribute zero
        information about that attribute from that task.

        Effects coding: deviation/sum-to-zero. For each attribute, the
        alphabetically-first level is the reference (-1 in all K-1
        columns); other levels are +1 in their own column, 0 elsewhere.
          - N = n_tasks * n_alts_per_task (one row per alternative)
          - p = sum(n_levels - 1) across attributes (estimable params)

        Range is approximately [0, 1]; an orthogonal balanced design
        with no within-task degeneracy hits ~1.0.

        Caveat: The MNL information matrix actually depends on assumed
        prior part-worths through the choice probabilities. We use the
        uniform-prior approximation (equiprobable choices), which
        simplifies the formula above and makes the metric a pure
        function of the design. Part-worth-aware D-efficiency is a
        future-work candidate.

    Numerical stability:
        Computed via numpy.linalg.slogdet to avoid overflow on |X'X|
        for designs with many parameters. If the design matrix is
        singular (sign <= 0 from slogdet), d_efficiency is reported
        as 0.0 and the gate fails, with a descriptive failed_gates
        message.
    """
    # ---- Sort attributes / levels deterministically ------------------------
    sorted_attrs = sorted(taxonomy.attributes, key=lambda a: a.id)

    # ---- Level balance -----------------------------------------------------
    n_alts_per_task = len(design.tasks[0].alternatives) if design.tasks else 0
    n_slots = len(design.tasks) * n_alts_per_task

    level_balance: dict[str, dict[str, float]] = {}
    worst_imbalance = 0.0
    worst_attr_id = ""
    worst_level_id = ""

    for attr in sorted_attrs:
        sorted_level_ids = sorted(lvl.id for lvl in attr.levels)
        n_levels = len(sorted_level_ids)
        counts: Counter[str] = Counter()
        for task in design.tasks:
            for alt in task.alternatives:
                counts[alt.levels[attr.id]] += 1

        # Frequencies in sorted level-id order so the dict has stable
        # iteration order (Python 3.7+ insertion-order-preserving dicts).
        attr_balance: dict[str, float] = {}
        for level_id in sorted_level_ids:
            freq = counts.get(level_id, 0) / n_slots if n_slots else 0.0
            attr_balance[level_id] = freq
            # Imbalance metric: |freq * n_levels - 1|. 0 = perfectly uniform.
            imbalance = abs(freq * n_levels - 1.0)
            if imbalance > worst_imbalance:
                worst_imbalance = imbalance
                worst_attr_id = attr.id
                worst_level_id = level_id
        level_balance[attr.id] = attr_balance

    # ---- Duplicate alternatives within a task -----------------------------
    # An alternative "duplicates" another within the same task iff their
    # full level vectors are identical. We count each alternative that
    # has at least one duplicate within its task. (So if a task has 3
    # identical alts, that contributes 3 to the count, not 2 or 1.)
    n_duplicate_alternatives = 0
    for task in design.tasks:
        # Convert each alt's levels dict to a hashable signature.
        # Sort by attr_id so the signature is order-independent.
        signatures = [
            tuple(sorted(alt.levels.items())) for alt in task.alternatives
        ]
        sig_counts = Counter(signatures)
        for sig in signatures:
            if sig_counts[sig] > 1:
                n_duplicate_alternatives += 1

    # ---- D-efficiency ------------------------------------------------------
    # Build effects-coded design matrix X.
    # For each attribute with K levels, contribute K-1 columns. The
    # alphabetically-first level (in sorted_level_ids[0]) is the reference.
    # Encoding for level k:
    #   - reference level: -1 in every column for this attribute
    #   - non-reference level k (1 <= k <= K-1): +1 in column k, 0 elsewhere
    p = sum(len(a.levels) - 1 for a in sorted_attrs)  # estimable params
    n_rows = n_slots

    if p == 0 or n_rows == 0:
        # Degenerate input: no estimable params (every attr has 1 level)
        # or empty design. Either way, D-efficiency is undefined. Report 0.
        d_efficiency = 0.0
    else:
        X = np.zeros((n_rows, p), dtype=np.float64)  # noqa: N806 — design matrix, statistical convention
        col_offsets: dict[str, int] = {}  # attr_id -> starting column
        col = 0
        for attr in sorted_attrs:
            col_offsets[attr.id] = col
            col += len(attr.levels) - 1

        row = 0
        for task in design.tasks:
            for alt in task.alternatives:
                for attr in sorted_attrs:
                    sorted_level_ids = sorted(lvl.id for lvl in attr.levels)
                    ref = sorted_level_ids[0]
                    chosen = alt.levels[attr.id]
                    base = col_offsets[attr.id]
                    if chosen == ref:
                        # All non-reference columns get -1
                        for j in range(len(attr.levels) - 1):
                            X[row, base + j] = -1.0
                    else:
                        # Find the index of `chosen` among non-reference
                        # levels (sorted_level_ids[1:]).
                        non_ref = sorted_level_ids[1:]
                        idx = non_ref.index(chosen)
                        X[row, base + idx] = 1.0
                row += 1

        # MNL information matrix uses task-centered design.
        # Reshape X to (n_tasks, n_alts_per_task, p) so we can subtract
        # each task's column means in one vectorized step.
        X_blocks = X.reshape(len(design.tasks), n_alts_per_task, p)  # noqa: N806
        # axis=1 means: average over alternatives within each task.
        # keepdims=True so the subtraction broadcasts cleanly.
        task_means = X_blocks.mean(axis=1, keepdims=True)
        X_centered = (X_blocks - task_means).reshape(n_rows, p)  # noqa: N806

        info_matrix = X_centered.T @ X_centered
        sign, log_abs_det = np.linalg.slogdet(info_matrix)
        if sign <= 0:  # noqa: SIM108 — branch is clearer than a 90-char ternary
            # Singular or non-positive-definite information matrix:
            # the design cannot identify all parameters (typically due
            # to within-task degeneracy on at least one attribute).
            d_efficiency = 0.0
        else:
            d_efficiency = float(np.exp(log_abs_det / p) / n_rows)

    # ---- Apply gates -------------------------------------------------------
    failed_gates: list[str] = []
    if d_efficiency < min_d_efficiency:
        failed_gates.append(
            f"d_efficiency {d_efficiency:.4f} < {min_d_efficiency:.4f} minimum"
        )
    if worst_imbalance > max_level_imbalance:
        failed_gates.append(
            f"level imbalance {worst_imbalance:.4f} > "
            f"{max_level_imbalance:.4f} maximum "
            f"(worst: attr={worst_attr_id!r} level={worst_level_id!r})"
        )

    return DesignReport(
        d_efficiency=d_efficiency,
        level_balance=level_balance,
        max_level_imbalance=worst_imbalance,
        n_duplicate_alternatives=n_duplicate_alternatives,
        passes_gates=len(failed_gates) == 0,
        failed_gates=failed_gates,
    )

