"""
Profile generator — turns EstimatedProfile into human/Claude-readable output.

Generates:
    - Archetype label (from top tenets)
    - Human-readable summary
    - Tradeoff examples ("1 day saved ≈ 4pp test coverage")
    - Compact preference string for Claude settings

Distinct from the EstimatedProfile (which is the math layer) — this is
the presentation layer. Same data, multiple framings.
"""

from __future__ import annotations

from kai.estimation.types import EstimatedProfile


def generate_profile_summary(profile: EstimatedProfile) -> dict:
    """Turn estimation output into structured summary. NOT YET IMPLEMENTED."""
    raise NotImplementedError
