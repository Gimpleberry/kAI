"""
Multinomial Logit (MNL) estimator for CBC choices.

Mathematically: assumes utility U_ij = sum_k(beta_k * x_ijk) + epsilon
where epsilon ~ Gumbel. Yields the familiar logit choice probability.

Estimated via maximum likelihood. Bootstrap resampling gives confidence
intervals around point estimates.

This is the workhorse — fast (seconds), proven, interpretable. Per ADR-002,
HB is not implemented; for single-respondent context with adequate tasks,
MNL is sufficient.
"""

from __future__ import annotations

from dataclasses import dataclass

from kai.estimation.types import EstimatedProfile
from kai.taxonomy.schema import Taxonomy


@dataclass(frozen=True)
class ChoiceObservation:
    """One observed choice from a CBC task."""

    task_id: int
    chosen_alt_index: int
    alternatives: list[dict[str, str]]  # each alt: attribute_id -> level_id


def estimate_mnl(
    observations: list[ChoiceObservation],
    taxonomy: Taxonomy,
    bootstrap_iters: int = 500,
    random_seed: int = 42,
) -> EstimatedProfile:
    """Estimate MNL part-worths via MLE with bootstrap CIs.

    NOT YET IMPLEMENTED — scaffolding stub.

    Implementation plan:
        1. Build design matrix using effects coding (K-1 dummies per attribute)
        2. Maximize log-likelihood via scipy.optimize (BFGS)
        3. Bootstrap respondent's choices to get part-worth distributions
        4. Compute attribute importance = (max_pw - min_pw) / sum across attrs
        5. Aggregate to tenet importance via taxonomy.related_tenets
        6. Package into EstimatedProfile
    """
    raise NotImplementedError("MNL estimation pending")
