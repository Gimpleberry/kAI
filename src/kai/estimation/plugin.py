"""
Estimation plugin — wraps MNL, MaxDiff, and ensemble estimators under
one lifecycle.

Per ADR-002, MNL is the only "real" estimator currently. This plugin
exists per Tenet 1's plugin pattern even though there's not much state
to manage at boot — the plugin contract makes future additions
(e.g., a thread pool for parallel bootstrap iterations) trivial to slot in.

Owns:
  - Plugin lifecycle for the estimation layer
  - Future home for parallel-bootstrap workers, caching, etc.

Depends on:
  - kai.shared
"""

from __future__ import annotations

import logging

logger = logging.getLogger("kai.estimation.plugin")


class EstimationPlugin:
    """Lifecycle wrapper for the estimation layer."""

    def start(self) -> None:
        logger.info("Estimation plugin ready (method=mnl)")

    def stop(self) -> None:
        pass
