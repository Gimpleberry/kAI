"""
Plugin base — common lifecycle contract every plugin module follows.

Per Tenet 1 (plugin pattern): every feature-module plugin class implements
this protocol so main.py can drive lifecycle uniformly.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Plugin(Protocol):
    """The contract main.py expects from anything in plugins.REGISTRY."""

    def start(self) -> None:
        """Called once at boot, after earlier plugins have started.

        Lightweight initialization only. Heavy work (network calls, file
        scans, expensive computations) should be deferred to post-boot
        jobs scheduled by the plugin (per Tenet 2).
        """
        ...

    def stop(self) -> None:
        """Called once at shutdown, in reverse boot order.

        Must be idempotent. If start() partially failed, stop() is still
        called and must not assume start() finished.
        """
        ...
