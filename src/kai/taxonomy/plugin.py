"""
Taxonomy plugin — loads and caches the validated taxonomy in memory.

Loads the taxonomy YAML once at boot and exposes it to other plugins
through a module-level reference. This avoids each downstream module
re-parsing and re-validating the YAML on every operation.

Owns:
  - One-time load + validation of config/taxonomy.yaml
  - Cached Taxonomy object accessible to other plugins

Depends on:
  - kai.shared
  - kai.taxonomy.loader (load_taxonomy)
"""

from __future__ import annotations

import logging

from kai.shared import TAXONOMY_PATH
from kai.taxonomy.loader import load_taxonomy
from kai.taxonomy.schema import Taxonomy

logger = logging.getLogger("kai.taxonomy.plugin")

# Module-level singleton — set by start(), cleared by stop()
_taxonomy: Taxonomy | None = None


def get_taxonomy() -> Taxonomy:
    """Return the cached taxonomy. Must be called after TaxonomyPlugin.start()."""
    if _taxonomy is None:
        raise RuntimeError(
            "Taxonomy not loaded. Did TaxonomyPlugin.start() run? "
            "If you're in a test or CLI context, call kai.taxonomy.loader.load_taxonomy() directly."
        )
    return _taxonomy


class TaxonomyPlugin:
    """Lifecycle wrapper for taxonomy loading."""

    def start(self) -> None:
        global _taxonomy
        _taxonomy = load_taxonomy(TAXONOMY_PATH)
        logger.info(
            "Taxonomy loaded (version=%s, attributes=%d, tenets=%d)",
            _taxonomy.version,
            len(_taxonomy.attributes),
            len(_taxonomy.tenets),
        )

    def stop(self) -> None:
        global _taxonomy
        _taxonomy = None
