"""
Direct rating calibrator.

CBC and MaxDiff both yield part-worths on a latent (unitless) scale.
Direct ratings let us anchor that scale to absolute terms.

Specifically: respondent rates the WORST and BEST level of each attribute
on a 1-7 scale. These ratings linearly map the latent part-worths to a
common interpretable scale, so attribute importances are comparable across
estimation runs.

This is also a sanity check — large divergence between rated importance
and CBC-derived importance is a "stated vs. revealed" gap, but now grounded
in proper choice data.
"""

from __future__ import annotations

from dataclasses import dataclass

from kai.estimation.types import EstimatedProfile


@dataclass(frozen=True)
class DirectRating:
    """A direct rating of an attribute level on the 1-7 scale."""

    attribute_id: str
    level_id: str
    rating: int  # 1-7


def calibrate_profile(
    profile: EstimatedProfile,
    ratings: list[DirectRating],
) -> EstimatedProfile:
    """Anchor the latent utility scale using direct ratings.

    NOT YET IMPLEMENTED.

    Implementation plan:
        1. For each attribute, fit linear map from latent part-worths to
           rated values (worst level -> low rating, best -> high)
        2. Apply same linear map to CIs (preserves uncertainty)
        3. Recompute importances on the anchored scale
        4. Return new EstimatedProfile with method="ensemble"
    """
    raise NotImplementedError("Rating calibration pending")
