"""
Profile plugin — wraps profile generation, export, and diffing under one
lifecycle.

Owns:
  - Plugin lifecycle for the profile layer

Depends on:
  - kai.shared
  - kai.estimation.types (EstimatedProfile)
"""

from __future__ import annotations

import logging

logger = logging.getLogger("kai.profile.plugin")


class ProfilePlugin:
    """Lifecycle wrapper for the profile layer."""

    def start(self) -> None:
        logger.info("Profile plugin ready")

    def stop(self) -> None:
        pass
