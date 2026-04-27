"""
Tests for the CBC design generator.

Coverage:
    - Output contract (CBCDesign returned with expected structure)
    - Level balance (each level appears within +/- 1 of perfect frequency)
    - Determinism (ADR-005: byte-identical pickle hashes for same inputs)
        ^ This is the Phase 1.3 backlog item, shipped alongside 1.1.
    - Argument validation (loud failures for bad input per Tenet 5)
    - Smoke test against the production taxonomy.yaml

The taxonomy fixtures here are constructed in-memory rather than loaded
from YAML so the bulk of these tests run without filesystem dependencies.
"""

from __future__ import annotations

import hashlib
import pickle
from collections import Counter

import pytest

from kai.design.cbc_generator import (
    Alternative,
    CBCDesign,
    ChoiceTask,
    generate_cbc_design,
)
from kai.shared import REPO_ROOT
from kai.taxonomy.schema import Attribute, Level, Taxonomy, Tenet

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _two_attribute_taxonomy() -> Taxonomy:
    """Small taxonomy: one 3-level attr, one 2-level attr. Fast tests."""
    return Taxonomy(
        version="test-1.0",
        tenets=[
            Tenet(id="quality", name="Quality", user_definition="QC over speed"),
            Tenet(id="speed", name="Speed", user_definition="Ship fast"),
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


def _hash_design(design: CBCDesign) -> str:
    """Hash a design via pickle for byte-identical comparison."""
    return hashlib.sha256(pickle.dumps(design, protocol=5)).hexdigest()


# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------


class TestOutputContract:
    def test_returns_cbcdesign(self) -> None:
        tax = _two_attribute_taxonomy()
        design = generate_cbc_design(tax, n_tasks=4, n_alts_per_task=3, seed=1)
        assert isinstance(design, CBCDesign)

    def test_correct_n_tasks_and_alts(self) -> None:
        tax = _two_attribute_taxonomy()
        design = generate_cbc_design(tax, n_tasks=10, n_alts_per_task=4, seed=1)
        assert len(design.tasks) == 10
        for task in design.tasks:
            assert isinstance(task, ChoiceTask)
            assert len(task.alternatives) == 4
            for alt in task.alternatives:
                assert isinstance(alt, Alternative)

    def test_task_ids_zero_indexed_sequential(self) -> None:
        tax = _two_attribute_taxonomy()
        design = generate_cbc_design(tax, n_tasks=5, n_alts_per_task=2, seed=1)
        assert [t.task_id for t in design.tasks] == [0, 1, 2, 3, 4]

    def test_every_alternative_has_all_attributes(self) -> None:
        tax = _two_attribute_taxonomy()
        expected = {a.id for a in tax.attributes}
        design = generate_cbc_design(tax, n_tasks=3, n_alts_per_task=2, seed=1)
        for task in design.tasks:
            for alt in task.alternatives:
                assert set(alt.levels.keys()) == expected

    def test_all_levels_valid_for_their_attribute(self) -> None:
        tax = _two_attribute_taxonomy()
        valid = {a.id: {lvl.id for lvl in a.levels} for a in tax.attributes}
        design = generate_cbc_design(tax, n_tasks=5, n_alts_per_task=3, seed=1)
        for task in design.tasks:
            for alt in task.alternatives:
                for attr_id, level_id in alt.levels.items():
                    assert level_id in valid[attr_id], (
                        f"Invalid level {level_id!r} for attribute {attr_id!r}"
                    )

    def test_d_efficiency_is_none_in_phase_1_1(self) -> None:
        # Per ADR-005 + the module docstring: diagnostics fills this in 1.2.
        tax = _two_attribute_taxonomy()
        design = generate_cbc_design(tax, n_tasks=4, n_alts_per_task=2, seed=1)
        assert design.d_efficiency is None

    def test_method_and_seed_recorded(self) -> None:
        tax = _two_attribute_taxonomy()
        design = generate_cbc_design(tax, n_tasks=4, n_alts_per_task=2, seed=42)
        assert design.method == "balanced_overlap"
        assert design.seed == 42


# ---------------------------------------------------------------------------
# Level balance
# ---------------------------------------------------------------------------


class TestLevelBalance:
    def test_perfect_balance_when_evenly_divisible(self) -> None:
        # 6 tasks * 2 alts = 12 slots; 3 levels => each appears 4 times.
        tax = _two_attribute_taxonomy()
        design = generate_cbc_design(tax, n_tasks=6, n_alts_per_task=2, seed=1)
        counts: Counter[str] = Counter()
        for task in design.tasks:
            for alt in task.alternatives:
                counts[alt.levels["coverage"]] += 1
        assert counts["low"] == counts["med"] == counts["high"] == 4

    def test_near_balance_when_not_evenly_divisible(self) -> None:
        # 5 tasks * 2 alts = 10 slots; 3 levels => base=3, rem=1.
        # Sorted level ids alphabetically: ['high', 'low', 'med'];
        # the FIRST sorted id ('high') gets the +1.
        tax = _two_attribute_taxonomy()
        design = generate_cbc_design(tax, n_tasks=5, n_alts_per_task=2, seed=1)
        counts: Counter[str] = Counter()
        for task in design.tasks:
            for alt in task.alternatives:
                counts[alt.levels["coverage"]] += 1
        assert sum(counts.values()) == 10
        assert counts["high"] == 4
        assert counts["low"] == 3
        assert counts["med"] == 3

    def test_two_level_attribute_balanced(self) -> None:
        tax = _two_attribute_taxonomy()
        design = generate_cbc_design(tax, n_tasks=10, n_alts_per_task=2, seed=1)
        counts: Counter[str] = Counter()
        for task in design.tasks:
            for alt in task.alternatives:
                counts[alt.levels["timeline"]] += 1
        # 20 slots / 2 levels => 10 each
        assert counts["fast"] == 10
        assert counts["slow"] == 10

    def test_max_imbalance_under_15_percent_gate(self) -> None:
        # The shared.QUALITY_GATE max_level_imbalance gate is 0.15.
        # Confirm our worst case stays well below that for realistic sizes.
        tax = _two_attribute_taxonomy()
        # 7 tasks * 4 alts = 28 slots; 3 levels => base=9, rem=1.
        # Levels: 10, 9, 9. Max deviation from uniform (28/3 ~= 9.33):
        # |10 - 9.33| / 9.33 ~= 0.071, well under 0.15.
        design = generate_cbc_design(tax, n_tasks=7, n_alts_per_task=4, seed=3)
        counts: Counter[str] = Counter()
        for task in design.tasks:
            for alt in task.alternatives:
                counts[alt.levels["coverage"]] += 1
        n_slots = 28
        n_levels = 3
        target = n_slots / n_levels
        max_dev = max(abs(c - target) for c in counts.values()) / target
        assert max_dev < 0.15


# ---------------------------------------------------------------------------
# Determinism (ADR-005 contract; covers Phase 1.3)
# ---------------------------------------------------------------------------


class TestDeterminism:
    """ADR-005: byte-identical output for same (taxonomy, params, seed)."""

    def test_same_seed_byte_identical(self) -> None:
        tax = _two_attribute_taxonomy()
        d1 = generate_cbc_design(tax, n_tasks=8, n_alts_per_task=3, seed=42)
        d2 = generate_cbc_design(tax, n_tasks=8, n_alts_per_task=3, seed=42)
        assert _hash_design(d1) == _hash_design(d2)

    @pytest.mark.parametrize("seed", [0, 1, 7, 42, 999, 2026])
    def test_determinism_holds_across_multiple_seeds(self, seed: int) -> None:
        tax = _two_attribute_taxonomy()
        d1 = generate_cbc_design(tax, n_tasks=6, n_alts_per_task=2, seed=seed)
        d2 = generate_cbc_design(tax, n_tasks=6, n_alts_per_task=2, seed=seed)
        assert _hash_design(d1) == _hash_design(d2)

    def test_different_seeds_produce_different_designs(self) -> None:
        # Sanity: the seed actually does something.
        tax = _two_attribute_taxonomy()
        d1 = generate_cbc_design(tax, n_tasks=8, n_alts_per_task=3, seed=1)
        d2 = generate_cbc_design(tax, n_tasks=8, n_alts_per_task=3, seed=2)
        assert _hash_design(d1) != _hash_design(d2)

    def test_different_taxonomy_produces_different_design(self) -> None:
        # Two-attr vs single-attr taxonomy at same seed/params must differ.
        tax_full = _two_attribute_taxonomy()
        tax_one = Taxonomy(
            version="test-min",
            tenets=[Tenet(id="quality", name="Quality", user_definition="QC")],
            attributes=[
                Attribute(
                    id="coverage",
                    name="Coverage",
                    description="x",
                    related_tenets=["quality"],
                    levels=[
                        Level(id="low", display="60%"),
                        Level(id="med", display="80%"),
                        Level(id="high", display="95%"),
                    ],
                )
            ],
        )
        d1 = generate_cbc_design(tax_full, n_tasks=4, n_alts_per_task=2, seed=42)
        d2 = generate_cbc_design(tax_one, n_tasks=4, n_alts_per_task=2, seed=42)
        assert _hash_design(d1) != _hash_design(d2)


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_orthogonal_method_raises_not_implemented(self) -> None:
        tax = _two_attribute_taxonomy()
        with pytest.raises(NotImplementedError, match="orthogonal"):
            generate_cbc_design(
                tax, n_tasks=4, n_alts_per_task=2, method="orthogonal", seed=1
            )

    def test_random_method_raises_not_implemented(self) -> None:
        tax = _two_attribute_taxonomy()
        with pytest.raises(NotImplementedError, match="random"):
            generate_cbc_design(
                tax, n_tasks=4, n_alts_per_task=2, method="random", seed=1
            )

    def test_unknown_method_raises_value_error(self) -> None:
        tax = _two_attribute_taxonomy()
        with pytest.raises(ValueError, match="Unknown method"):
            generate_cbc_design(
                tax, n_tasks=4, n_alts_per_task=2, method="bogus", seed=1
            )

    def test_n_tasks_zero_raises(self) -> None:
        tax = _two_attribute_taxonomy()
        with pytest.raises(ValueError, match="n_tasks"):
            generate_cbc_design(tax, n_tasks=0, n_alts_per_task=2, seed=1)

    def test_n_tasks_negative_raises(self) -> None:
        tax = _two_attribute_taxonomy()
        with pytest.raises(ValueError, match="n_tasks"):
            generate_cbc_design(tax, n_tasks=-1, n_alts_per_task=2, seed=1)

    def test_n_alts_too_small_raises(self) -> None:
        tax = _two_attribute_taxonomy()
        with pytest.raises(ValueError, match="n_alts_per_task"):
            generate_cbc_design(tax, n_tasks=4, n_alts_per_task=1, seed=1)


# ---------------------------------------------------------------------------
# Production-config smoke test
# ---------------------------------------------------------------------------


class TestProductionConfig:
    """Smoke test against the real config/taxonomy.yaml at production sizes."""

    def test_full_taxonomy_at_production_size(self) -> None:
        from kai.taxonomy.loader import load_taxonomy

        real_taxonomy = REPO_ROOT / "config" / "taxonomy.yaml"
        if not real_taxonomy.exists():
            pytest.skip(f"Real taxonomy not present at {real_taxonomy}")

        tax = load_taxonomy(real_taxonomy)
        # Production design_params: 20 tasks * 4 alts.
        design = generate_cbc_design(tax, n_tasks=20, n_alts_per_task=4, seed=42)

        assert len(design.tasks) == 20
        for task in design.tasks:
            assert len(task.alternatives) == 4
            for alt in task.alternatives:
                assert len(alt.levels) == len(tax.attributes)

        # Every attribute's levels should be near-balanced (max deviation
        # well under the 15% gate from design_params.yaml).
        for attr in tax.attributes:
            counts: Counter[str] = Counter()
            for task in design.tasks:
                for alt in task.alternatives:
                    counts[alt.levels[attr.id]] += 1
            n_slots = 20 * 4
            target = n_slots / len(attr.levels)
            max_dev = max(abs(c - target) for c in counts.values()) / target
            assert max_dev < 0.15, (
                f"Attribute {attr.id!r} imbalance {max_dev:.3f} >= 0.15 gate"
            )
