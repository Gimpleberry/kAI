"""
plugins.py — Feature registry. One line per feature, in boot order.

Per ARCHITECTURE_TENETS Tenet 1 plugin pattern.

Conventions:
  - Each feature is a self-contained module with a Plugin class
    exposing start() and stop() lifecycle methods.
  - Adding a feature: create the module, add one line here.
  - Disabling a feature: comment out one line. Nothing breaks.
  - Boot order matters: state-creating plugins (DB init) load BEFORE
    consumers (design generators, estimators, API server).

Boot order rationale (top-to-bottom = first-to-last):
    1. STORAGE       — Database schema must exist before anything reads/writes
    2. TAXONOMY      — Validates and caches the taxonomy in memory
    3. DESIGN        — CBC + MaxDiff generators (depend on taxonomy)
    4. ESTIMATION    — MNL + ensemble estimators (depend on taxonomy)
    5. PROFILE       — Profile generation/export (depends on estimation types)
    6. ELICITATION   — FastAPI server (depends on all the above being ready)

The validation script asserts:
  - Every imported plugin class implements start()/stop()
  - No plugin defines anything that lives in shared.py
  - Boot order has no cycles
"""

from __future__ import annotations

# Storage — must come first, creates DB schema and validates connection
from kai.storage.plugin import StoragePlugin

# Taxonomy — loads + caches the validated taxonomy in memory
from kai.taxonomy.plugin import TaxonomyPlugin

# Design — CBC and MaxDiff generators
from kai.design.plugin import DesignPlugin

# Estimation — MNL workhorse plus ensemble combiner
from kai.estimation.plugin import EstimationPlugin

# Profile — turns EstimatedProfile into exportable formats
from kai.profile.plugin import ProfilePlugin

# Elicitation — FastAPI server, last because it serves everything else
from kai.elicitation.plugin import ElicitationPlugin


# =============================================================================
# Registry — list-of-plugins in boot order
# =============================================================================
# To disable a plugin, comment out its line. To add one, instantiate and
# append. The lifecycle runner (main.py) iterates this list for startup
# and reverses it for shutdown.

REGISTRY: list = [
    StoragePlugin(),
    TaxonomyPlugin(),
    DesignPlugin(),
    EstimationPlugin(),
    ProfilePlugin(),
    ElicitationPlugin(),
]
