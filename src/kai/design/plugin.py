"""
Design plugin — wraps CBC and MaxDiff design generation under one lifecycle.

Per ADR-005, designs themselves are not stored — only seeds and parameters.
This plugin holds no persistent state; its start()/stop() methods are
mostly nominal, but the plugin exists so:
  - It can be enabled/disabled by commenting out one line in plugins.py
  - It can be tested for plugin protocol conformance via main.py --check
  - Future additions (e.g., design caching, generation worker pool) have
    a natural home

Owns:
  - Plugin-level access to the design generators
  - Coordinated version reporting

Depends on:
  - kai.shared (CBC_GENERATOR_VERSION, MAXDIFF_GENERATOR_VERSION)
  - kai.taxonomy.plugin (cached taxonomy)
"""

from __future__ import annotations

import logging

from kai.shared import CBC_GENERATOR_VERSION, MAXDIFF_GENERATOR_VERSION

logger = logging.getLogger("kai.design.plugin")


class DesignPlugin:
    """Lifecycle wrapper for the design generation layer."""

    def start(self) -> None:
        logger.info(
            "Design plugin ready (cbc_gen=%s, maxdiff_gen=%s)",
            CBC_GENERATOR_VERSION,
            MAXDIFF_GENERATOR_VERSION,
        )

    def stop(self) -> None:
        pass
