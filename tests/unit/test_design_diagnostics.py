"""
Tests for the CBC design diagnostics.

Coverage:
    - Output contract (DesignReport with all fields populated)
    - Level balance (dict shape, frequencies, max-imbalance metric)
    - D-efficiency (hand-verifiable orthogonal case, singular design)
    - Duplicate alternative detection
    - Gate logic (pass/fail, failed_gates messages)
    - Default thresholds pulled from shared.py (Tenet 1)
    - Determinism (pure function of input)
    - Production-config sentinel test for BACKLOG 1.1.5 (see test docstring)
"""

from __future__ import annotations

import inspect

import pytest

from kai.design.cbc_generator import (
    Alternative,
    CBCDesign,
    ChoiceTask,
    generate_cbc_design,
)
from kai.design.design_diagnostics import DesignReport, diagnose_cbc_design
from kai.shared import (
    QUALITY_GATE_MAX_LEVEL_IMBALANCE,
    QUALITY_GATE_MIN_D_EFFICIENCY,
    REPO_ROOT,
)
from kai.taxonomy.schema import Attribute, Level, Taxonomy, Tenet

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _two_attribute_taxonomy() -> Taxonomy:
    """Small taxonomy: one 3-level attr, one 2-level attr."""
    return Taxonomy(
        version="test-1.0",
        tenets=[
            Tenet(id="quality", name="Q", user_definition="QC"),
            Tenet(id="speed", name="S", user_definition="ship"),
        ],
        attributes=[
            Attribute(
                id="coverage",
                name="Coverage",
                description="Test coverage",
                related_tenets=["quality"],
                levels=[
                    Level(id="low", display="60%"),
                    Level(id="med", display="80%"),
                    Level(id="high", display="95%"),
                ],
            ),
            Attribute(
                id="timeline",
                name="Timeline",
                description="Time to ship",
                related_tenets=["speed"],
                levels=[
                    Level(id="fast", display="2 days"),
                    Level(id="slow", display="3 weeks"),
                ],
            ),
        ],
    )


def _orthogonal_2x2_taxonomy() -> Taxonomy:
    """Two 2-level attrs. With levels named 'aa'/'bb', 'aa' is the
    alphabetically-first (reference) level under our effects coding."""
    return Taxonomy(
        version="orth-2x2",
        tenets=[Tenet(id="t", name="T", user_definition="T")],
        attributes=[
            Attribute(
                id="x", name="X", description="x", related_tenets=["t"],
                levels=[Level(id="aa", display="A"), Level(id="bb", display="B")],
            ),
            Attribute(
                id="y", name="Y", description="x", related_tenets=["t"],
                levels=[Level(id="aa", display="A"), Level(id="bb", display="B")],
            ),
        ],
    )


def _make_design(tasks_specs: list[list[dict[str, str]]]) -> CBCDesign:
    """Build a CBCDesign from a list-of-lists of level dicts."""
    tasks = [
        ChoiceTask(
            task_id=i,
            alternatives=[Alternative(levels=alt) for alt in task_alts],
        )
        for i, task_alts in enumerate(tasks_specs)
    ]
    return CBCDesign(tasks=tasks, method="balanced_overlap", seed=0,
                     d_efficiency=None)


# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------


class TestOutputContract:
    def test_returns_design_report(self) -> None:
        tax = _two_attribute_taxonomy()
        design = generate_cbc_design(tax, n_tasks=10, n_alts_per_task=4, seed=1)
        report = diagnose_cbc_design(design, tax)
        assert isinstance(report, DesignReport)

    def test_all_fields_populated(self) -> None:
        tax = _two_attribute_taxonomy()
        design = generate_cbc_design(tax, n_tasks=10, n_alts_per_task=4, seed=1)
        report = diagnose_cbc_design(design, tax)
        assert isinstance(report.d_efficiency, float)
        assert isinstance(report.level_balance, dict)
        assert isinstance(report.max_level_imbalance, float)
        assert isinstance(report.n_duplicate_alternatives, int)
        assert isinstance(report.passes_gates, bool)
        assert isinstance(report.failed_gates, list)

    def test_level_balance_has_all_attributes(self) -> None:
        tax = _two_attribute_taxonomy()
        design = generate_cbc_design(tax, n_tasks=5, n_alts_per_task=3, seed=1)
        report = diagnose_cbc_design(design, tax)
        assert set(report.level_balance.keys()) == {"coverage", "timeline"}

    def test_level_balance_has_all_levels_per_attribute(self) -> None:
        tax = _two_attribute_taxonomy()
        design = generate_cbc_design(tax, n_tasks=5, n_alts_per_task=3, seed=1)
        report = diagnose_cbc_design(design, tax)
        assert set(report.level_balance["coverage"].keys()) == {"low", "med", "high"}
        assert set(report.level_balance["timeline"].keys()) == {"fast", "slow"}


# ---------------------------------------------------------------------------
# Level balance
# ---------------------------------------------------------------------------


class TestLevelBalance:
    def test_frequencies_sum_to_one_per_attribute(self) -> None:
        tax = _two_attribute_taxonomy()
        design = generate_cbc_design(tax, n_tasks=10, n_alts_per_task=4, seed=1)
        report = diagnose_cbc_design(design, tax)
        for attr_id, freqs in report.level_balance.items():
            assert abs(sum(freqs.values()) - 1.0) < 1e-10, (
                f"Attribute {attr_id!r} frequencies sum to {sum(freqs.values())}"
            )

    def test_two_level_attribute_perfectly_balanced(self) -> None:
        # 10 tasks * 4 alts = 40 slots / 2 levels = 20 each => freq 0.5
        tax = _two_attribute_taxonomy()
        design = generate_cbc_design(tax, n_tasks=10, n_alts_per_task=4, seed=1)
        report = diagnose_cbc_design(design, tax)
        assert report.level_balance["timeline"]["fast"] == 0.5
        assert report.level_balance["timeline"]["slow"] == 0.5

    def test_imbalance_zero_when_perfectly_uniform(self) -> None:
        # Build by hand: attr 'x' (2 levels) with exactly 50/50 split.
        tax = _orthogonal_2x2_taxonomy()
        design = _make_design([
            [{"x": "aa", "y": "aa"}, {"x": "bb", "y": "bb"}],
            [{"x": "aa", "y": "bb"}, {"x": "bb", "y": "aa"}],
        ])
        report = diagnose_cbc_design(design, tax)
        assert report.max_level_imbalance == 0.0

    def test_imbalance_correct_for_skewed_design(self) -> None:
        # 3 of 4 alts have x="aa". freq("aa") = 0.75, n_levels=2.
        # imbalance = |0.75 * 2 - 1| = 0.5
        tax = _orthogonal_2x2_taxonomy()
        design = _make_design([
            [{"x": "aa", "y": "aa"}, {"x": "aa", "y": "bb"}],
            [{"x": "aa", "y": "aa"}, {"x": "bb", "y": "bb"}],
        ])
        report = diagnose_cbc_design(design, tax)
        assert report.max_level_imbalance == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# D-efficiency
# ---------------------------------------------------------------------------


class TestDEfficiency:
    def test_orthogonal_2x2_design_d_eff_is_one(self) -> None:
        """Hand-verifiable case: 1 task with 4 alts forming an orthogonal
        2-attribute, 2-level design. Effects coding gives X with rows
        (+1,+1), (+1,-1), (-1,+1), (-1,-1). Within-task means are zero,
        so centered X = X. X'X = diag(4,4); det=16; p=2; N=4.
        D-eff = 16^(1/2) / 4 = 1.0."""
        tax = _orthogonal_2x2_taxonomy()
        design = _make_design([
            [
                {"x": "bb", "y": "bb"},
                {"x": "bb", "y": "aa"},
                {"x": "aa", "y": "bb"},
                {"x": "aa", "y": "aa"},
            ],
        ])
        report = diagnose_cbc_design(design, tax)
        assert report.d_efficiency == pytest.approx(1.0, abs=1e-10)

    def test_singular_design_d_eff_is_zero(self) -> None:
        """Design where attr 'x' is constant across all alts in every task.
        The MNL information matrix becomes singular (centered column for
        x is zero), so D-eff is reported as 0.0 and the gate fails with
        a descriptive message."""
        tax = _orthogonal_2x2_taxonomy()
        design = _make_design([
            [
                {"x": "aa", "y": "aa"},
                {"x": "aa", "y": "bb"},
                {"x": "aa", "y": "aa"},
                {"x": "aa", "y": "bb"},
            ],
        ])
        report = diagnose_cbc_design(design, tax)
        assert report.d_efficiency == 0.0
        assert not report.passes_gates
        assert any("d_efficiency" in msg for msg in report.failed_gates)

    def test_d_eff_is_pure_function_of_design(self) -> None:
        """Determinism: same input always produces same D-efficiency.
        (Diagnostics aren't randomized - this is a sanity check, not a
        contract obligation like ADR-005's seed determinism.)"""
        tax = _two_attribute_taxonomy()
        design = generate_cbc_design(tax, n_tasks=10, n_alts_per_task=4, seed=1)
        r1 = diagnose_cbc_design(design, tax)
        r2 = diagnose_cbc_design(design, tax)
        assert r1.d_efficiency == r2.d_efficiency
        assert r1.level_balance == r2.level_balance
        assert r1.max_level_imbalance == r2.max_level_imbalance


# ---------------------------------------------------------------------------
# Duplicate alternatives
# ---------------------------------------------------------------------------


class TestDuplicateDetection:
    def test_no_duplicates_detected_when_all_distinct(self) -> None:
        tax = _orthogonal_2x2_taxonomy()
        design = _make_design([
            [
                {"x": "aa", "y": "aa"},
                {"x": "aa", "y": "bb"},
                {"x": "bb", "y": "aa"},
                {"x": "bb", "y": "bb"},
            ],
        ])
        report = diagnose_cbc_design(design, tax)
        assert report.n_duplicate_alternatives == 0

    def test_all_three_alts_identical_counts_three(self) -> None:
        tax = _orthogonal_2x2_taxonomy()
        design = _make_design([
            [
                {"x": "aa", "y": "aa"},
                {"x": "aa", "y": "aa"},
                {"x": "aa", "y": "aa"},
            ],
        ])
        report = diagnose_cbc_design(design, tax)
        assert report.n_duplicate_alternatives == 3

    def test_one_pair_duplicates_counts_two(self) -> None:
        # 3 alts: A, A, B -> the two A's are duplicates; B is not.
        tax = _orthogonal_2x2_taxonomy()
        design = _make_design([
            [
                {"x": "aa", "y": "bb"},
                {"x": "aa", "y": "bb"},
                {"x": "bb", "y": "aa"},
            ],
        ])
        report = diagnose_cbc_design(design, tax)
        assert report.n_duplicate_alternatives == 2

    def test_duplicates_summed_across_tasks(self) -> None:
        # Task 0: 3 dups. Task 1: 0 dups. Task 2: 2 dups (one pair).
        tax = _orthogonal_2x2_taxonomy()
        design = _make_design([
            [
                {"x": "aa", "y": "aa"},
                {"x": "aa", "y": "aa"},
                {"x": "aa", "y": "aa"},
            ],
            [
                {"x": "aa", "y": "aa"},
                {"x": "bb", "y": "aa"},
                {"x": "aa", "y": "bb"},
            ],
            [
                {"x": "aa", "y": "bb"},
                {"x": "aa", "y": "bb"},
                {"x": "bb", "y": "aa"},
            ],
        ])
        report = diagnose_cbc_design(design, tax)
        assert report.n_duplicate_alternatives == 5


# ---------------------------------------------------------------------------
# Gate logic
# ---------------------------------------------------------------------------


class TestGateLogic:
    def test_strict_d_eff_threshold_triggers_failure(self) -> None:
        tax = _two_attribute_taxonomy()
        design = generate_cbc_design(tax, n_tasks=10, n_alts_per_task=4, seed=1)
        # Push threshold above any realistic D-eff.
        report = diagnose_cbc_design(design, tax, min_d_efficiency=0.999)
        assert not report.passes_gates
        assert any("d_efficiency" in msg for msg in report.failed_gates)

    def test_strict_imbalance_threshold_triggers_failure(self) -> None:
        tax = _two_attribute_taxonomy()
        design = generate_cbc_design(tax, n_tasks=10, n_alts_per_task=4, seed=1)
        # Threshold of 0 means no imbalance tolerated at all.
        report = diagnose_cbc_design(design, tax, max_level_imbalance=0.0)
        assert not report.passes_gates
        assert any("imbalance" in msg for msg in report.failed_gates)

    def test_failed_gate_messages_are_descriptive(self) -> None:
        tax = _two_attribute_taxonomy()
        design = generate_cbc_design(tax, n_tasks=10, n_alts_per_task=4, seed=1)
        report = diagnose_cbc_design(design, tax, min_d_efficiency=0.999)
        msg = report.failed_gates[0]
        # Must mention what was measured and what the threshold was.
        assert "d_efficiency" in msg
        assert any(c.isdigit() for c in msg)
        assert "<" in msg or ">" in msg or "minimum" in msg

    def test_passes_gates_iff_failed_gates_empty(self) -> None:
        tax = _two_attribute_taxonomy()
        design = generate_cbc_design(tax, n_tasks=10, n_alts_per_task=4, seed=1)
        report = diagnose_cbc_design(design, tax)
        assert report.passes_gates == (len(report.failed_gates) == 0)


# ---------------------------------------------------------------------------
# Default thresholds (Tenet 1)
# ---------------------------------------------------------------------------


class TestDefaultThresholds:
    """Defaults must come from shared.py constants, not literals.
    See ARCHITECTURE_TENETS Tenet 1: cross-cutting thresholds belong in
    shared.py and every other module imports from there."""

    def test_default_min_d_efficiency_matches_shared(self) -> None:
        sig = inspect.signature(diagnose_cbc_design)
        assert sig.parameters["min_d_efficiency"].default == QUALITY_GATE_MIN_D_EFFICIENCY

    def test_default_max_level_imbalance_matches_shared(self) -> None:
        sig = inspect.signature(diagnose_cbc_design)
        assert sig.parameters["max_level_imbalance"].default == QUALITY_GATE_MAX_LEVEL_IMBALANCE


# ---------------------------------------------------------------------------
# Production-config sentinel (BACKLOG 1.1.5)
# ---------------------------------------------------------------------------


class TestProductionConfigSentinel:
    """Phase 1.2 ships diagnostics correctness; the gate failure on the
    Phase 1.1 generator's output is itself the result of running them.

    The Phase 1.1 generator's level-balanced independent shuffles produce
    D-efficiency ~0.38 at production scale, statistically indistinguishable
    from pure random sampling. This is well below the 0.85 gate, which is
    calibrated against full Sawtooth-style balanced overlap with swap-based
    D-eff optimization.

    BACKLOG item 1.1.5 will add swap-based optimization to the generator.
    Once it lands, this assertion flips: prod design will pass the gate.

    Until then, this test is a deliberate sentinel:
      - If it KEEPS failing: 1.1.5 hasn't shipped yet (expected).
      - If it starts PASSING: either 1.1.5 has shipped (great, flip the
        assertion) or someone weakened the gate threshold (investigate).
    """

    def test_production_design_intentionally_fails_d_eff_gate(self) -> None:
        from kai.taxonomy.loader import load_taxonomy

        real_taxonomy = REPO_ROOT / "config" / "taxonomy.yaml"
        if not real_taxonomy.exists():
            pytest.skip(f"Real taxonomy not present at {real_taxonomy}")

        tax = load_taxonomy(real_taxonomy)
        design = generate_cbc_design(tax, n_tasks=20, n_alts_per_task=4, seed=42)
        report = diagnose_cbc_design(design, tax)

        # Sentinel: gate must FAIL until 1.1.5 ships.
        assert not report.passes_gates, (
            f"Production design unexpectedly PASSES gates with d_eff="
            f"{report.d_efficiency:.4f}. Either BACKLOG 1.1.5 (swap-based "
            f"D-eff optimization) has shipped - in which case flip this "
            f"assertion to expect passes_gates=True - or the threshold "
            f"has been weakened. Investigate."
        )
        assert any("d_efficiency" in m for m in report.failed_gates)
        # Bound the expected range so a wildly-off measurement (e.g. ~0.0
        # from a regression that breaks the formula) still trips the test.
        assert 0.30 <= report.d_efficiency <= 0.50, (
            f"Production D-eff {report.d_efficiency:.4f} outside expected "
            f"[0.30, 0.50] range for level-balanced indep shuffles. "
            f"Either the generator changed or the metric did."
        )

    def test_production_design_passes_imbalance_gate(self) -> None:
        """Level-balance gate IS expected to pass - that's what 1.1's
        algorithm actually optimizes for."""
        from kai.taxonomy.loader import load_taxonomy

        real_taxonomy = REPO_ROOT / "config" / "taxonomy.yaml"
        if not real_taxonomy.exists():
            pytest.skip(f"Real taxonomy not present at {real_taxonomy}")

        tax = load_taxonomy(real_taxonomy)
        design = generate_cbc_design(tax, n_tasks=20, n_alts_per_task=4, seed=42)
        report = diagnose_cbc_design(design, tax)
        assert report.max_level_imbalance <= QUALITY_GATE_MAX_LEVEL_IMBALANCE

