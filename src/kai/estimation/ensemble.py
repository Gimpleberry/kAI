"""
Ensemble estimator — combines CBC, MaxDiff, and direct ratings.

The hybrid framework means each signal gets weighted by its information value:

    - CBC provides the most information (10s of choices × multiple attrs)
    - MaxDiff cross-validates tenet-level importances
    - Direct ratings anchor the absolute scale

The ensemble is more robust than any single method:
    - CBC alone: best for tradeoff math, but unitless
    - MaxDiff alone: tenet importance only, no level effects
    - Ratings alone: scale-use bias, no revealed preference

Combined: tradeoff math + tenet validation + interpretable units.
"""

from __future__ import annotations

from kai.estimation.maxdiff_estimator import MaxDiffObservation
from kai.estimation.mnl import ChoiceObservation
from kai.estimation.rating_calibrator import DirectRating
from kai.estimation.types import EstimatedProfile
from kai.taxonomy.schema import Taxonomy


def estimate_ensemble(
    cbc_observations: list[ChoiceObservation],
    maxdiff_observations: list[MaxDiffObservation],
    direct_ratings: list[DirectRating],
    taxonomy: Taxonomy,
) -> EstimatedProfile:
    """Estimate a profile using all three signal sources.

    NOT YET IMPLEMENTED.

    Implementation plan:
        1. Run estimate_mnl() on CBC observations → CBC profile
        2. Run estimate_maxdiff() on MaxDiff observations → tenet utilities
        3. Cross-check: tenet importance from CBC aggregation vs MaxDiff
           Flag inconsistencies for diagnostics
        4. Run calibrate_profile() with direct ratings → anchored scale
        5. Return final EstimatedProfile with method="ensemble"
    """
    raise NotImplementedError("Ensemble estimation pending")
