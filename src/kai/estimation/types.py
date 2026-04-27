"""
Shared estimation types — the data contract every estimator returns.

This is THE most important data contract in the system. The frontend
displays it, the storage layer persists it, the profile generator reads
it, and downstream consumers (Claude preferences) export from it.

Every estimator (MNL, future Bayesian methods) MUST return an
EstimatedProfile so they're interchangeable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

EstimationMethod = Literal["mnl", "ensemble"]


@dataclass(frozen=True)
class LevelPartWorth:
    """Estimated utility for a single level."""

    level_id: str
    point_estimate: float
    ci_low: float   # 95% CI lower bound
    ci_high: float  # 95% CI upper bound
    std_error: float


@dataclass(frozen=True)
class AttributeUtility:
    """Part-worths for one attribute, plus derived importance."""

    attribute_id: str
    levels: list[LevelPartWorth]
    importance: float           # share of total utility range, in [0,1]
    importance_ci: tuple[float, float]


@dataclass(frozen=True)
class TenetImportance:
    """Aggregated importance for a tenet (sum of related attribute importances)."""

    tenet_id: str
    importance: float
    importance_ci: tuple[float, float]
    contributing_attributes: list[str]


@dataclass(frozen=True)
class EstimatedProfile:
    """Complete estimated preference profile.

    This is the canonical artifact — versioned, exportable, comparable.
    """

    version: str
    estimated_at: datetime
    method: EstimationMethod
    n_observations: int
    taxonomy_version: str

    attributes: list[AttributeUtility]
    tenets: list[TenetImportance]

    log_likelihood: float
    converged: bool
    diagnostics: dict[str, float]  # method-specific
