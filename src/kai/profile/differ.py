"""
Profile differ — compare two profile versions.

Useful for:
    - Tracking how preferences shift over time as you add more questions
    - Verifying that a re-estimation didn't drastically change the answer
      (sign of unstable estimation)
    - Showing the user what's changed since their last session
"""

from __future__ import annotations

from dataclasses import dataclass

from kai.estimation.types import EstimatedProfile


@dataclass(frozen=True)
class ProfileDiff:
    """Differences between two profiles."""

    importance_changes: dict[str, float]
    new_archetype: str | None  # if archetype flipped
    largest_shifts: list[tuple[str, float]]


def diff_profiles(old: EstimatedProfile, new: EstimatedProfile) -> ProfileDiff:
    """Compute differences. NOT YET IMPLEMENTED."""
    raise NotImplementedError
