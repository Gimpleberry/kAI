"""
main.py — Application entry point.

Run this to start the kAI service. It imports the plugin registry and
runs each plugin's start() method in registry order, then blocks until
shutdown signal, then runs stop() in reverse order.

Per Tenet 2 (efficient): heavy startup checks are deferred to post-boot
jobs scheduled by individual plugins, so the API server binds quickly
and is reachable immediately.

Usage:
    python main.py                  # Start the application
    python main.py --check          # Validate plugins load without starting
    python main.py --boot-order     # Print computed boot order and exit

For one-off operations (validate config, export profile, etc.), use the
CLI instead:
    kai --help

For development with hot reload, use uvicorn directly against the
elicitation plugin's app:
    uvicorn kai.elicitation.api:create_app --factory --reload
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
from typing import Any

from plugins import REGISTRY
from kai.shared import KaiError, get_config_value

logger = logging.getLogger("kai.main")


def _setup_logging() -> None:
    """Configure root logger from KAI_LOG_LEVEL env var."""
    level_name = get_config_value("LOG_LEVEL", default="INFO")
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def _check_plugins() -> int:
    """Validate that every registered plugin has start() and stop(). Per Tenet 5.

    Returns 0 on success, nonzero on any plugin missing required methods.
    """
    failed: list[str] = []
    for plugin in REGISTRY:
        cls_name = type(plugin).__name__
        if not callable(getattr(plugin, "start", None)):
            failed.append(f"{cls_name}: missing start() method")
        if not callable(getattr(plugin, "stop", None)):
            failed.append(f"{cls_name}: missing stop() method")

    if failed:
        for line in failed:
            print(f"✗ {line}", file=sys.stderr)
        return 1

    print(f"✓ {len(REGISTRY)} plugins valid")
    return 0


def _print_boot_order() -> int:
    """Print the registry in boot order, then in shutdown order."""
    print("Boot order (top-to-bottom = first-to-last):")
    for i, plugin in enumerate(REGISTRY, start=1):
        print(f"  {i:2d}. {type(plugin).__name__}")
    print()
    print("Shutdown order (reverse of boot):")
    for i, plugin in enumerate(reversed(REGISTRY), start=1):
        print(f"  {i:2d}. {type(plugin).__name__}")
    return 0


def _start_all(plugins: list[Any]) -> list[Any]:
    """Start plugins in registry order. Returns the list of successfully
    started plugins (so we can stop only those if startup partially fails).
    """
    started: list[Any] = []
    for plugin in plugins:
        cls_name = type(plugin).__name__
        try:
            logger.info("Starting %s", cls_name)
            plugin.start()
            started.append(plugin)
        except Exception:
            logger.exception("Failed to start %s — initiating shutdown", cls_name)
            raise
    return started


def _stop_all(started: list[Any]) -> None:
    """Stop plugins in reverse boot order. Logs but does not re-raise — we
    want shutdown to be best-effort even if one plugin's stop() fails."""
    for plugin in reversed(started):
        cls_name = type(plugin).__name__
        try:
            logger.info("Stopping %s", cls_name)
            plugin.stop()
        except Exception:
            logger.exception("Error stopping %s (continuing)", cls_name)


def main() -> int:
    parser = argparse.ArgumentParser(description="kAI application entry point")
    parser.add_argument("--check", action="store_true",
                        help="Validate plugin lifecycle methods, then exit")
    parser.add_argument("--boot-order", action="store_true",
                        help="Print boot/shutdown order, then exit")
    args = parser.parse_args()

    _setup_logging()

    if args.check:
        return _check_plugins()
    if args.boot_order:
        return _print_boot_order()

    started: list[Any] = []
    try:
        started = _start_all(REGISTRY)

        # Block until SIGINT/SIGTERM. The elicitation plugin owns the actual
        # serving loop; this main thread just waits for shutdown signal.
        signal.sigwait([signal.SIGINT, signal.SIGTERM])  # type: ignore[attr-defined]
    except KaiError:
        logger.exception("kAI startup failed")
        return 2
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt — shutting down")
    finally:
        _stop_all(started)

    return 0


if __name__ == "__main__":
    sys.exit(main())
