"""
MaxDiff (best-worst scaling) task generator.

For tenet-level prioritization. Each task shows N items (tenets); respondent
picks the most and least important. Mathematically equivalent to ranking
but cognitively much easier.

Uses balanced incomplete block design (BIBD) so:
    - Each item appears in roughly equal numbers of tasks
    - Each pair of items co-appears in roughly equal numbers of tasks

This balance is what lets us recover unbiased item utilities.
"""

from __future__ import annotations

from dataclasses import dataclass

from kai.taxonomy.schema import Taxonomy


@dataclass(frozen=True)
class MaxDiffTask:
    """A best/worst selection task."""

    task_id: int
    item_ids: list[str]  # tenet ids shown in this task


@dataclass(frozen=True)
class MaxDiffDesign:
    """Full MaxDiff questionnaire."""

    tasks: list[MaxDiffTask]
    method: str
    seed: int
    item_frequencies: dict[str, int]  # how often each item appears


def generate_maxdiff_design(
    taxonomy: Taxonomy,
    n_tasks: int,
    n_items_per_task: int,
    method: str = "bibd",
    seed: int = 42,
) -> MaxDiffDesign:
    """Generate a MaxDiff design.

    NOT YET IMPLEMENTED — scaffolding stub.

    Implementation plan:
        1. Items = tenet IDs from taxonomy
        2. Generate BIBD using known parameter combinations from pyDOE3
        3. Validate item frequency balance is within thresholds
        4. Return ordered task list
    """
    raise NotImplementedError("MaxDiff design generation pending")
