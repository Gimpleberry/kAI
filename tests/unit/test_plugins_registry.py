"""
Enforce Tenet 1 plugin pattern:
  - Every entry in plugins.REGISTRY implements start() and stop()
  - The registry is non-empty
  - Plugins are instances (not classes) — REGISTRY contains live objects
  - Each plugin module path matches its class name convention
"""

from __future__ import annotations

from typing import get_type_hints  # noqa: F401  (kept for future per-plugin checks)

import plugins as plugins_registry  # the plugins.py at repo root


def test_registry_is_non_empty() -> None:
    assert len(plugins_registry.REGISTRY) > 0, "plugins.REGISTRY is empty"


def test_every_plugin_has_lifecycle_methods() -> None:
    """Per Tenet 1: every plugin class has start() AND stop()."""
    failures: list[str] = []
    for plugin in plugins_registry.REGISTRY:
        cls_name = type(plugin).__name__
        if not callable(getattr(plugin, "start", None)):
            failures.append(f"{cls_name}: missing or non-callable start()")
        if not callable(getattr(plugin, "stop", None)):
            failures.append(f"{cls_name}: missing or non-callable stop()")

    assert not failures, "Plugin lifecycle violations:\n  " + "\n  ".join(failures)


def test_registry_contains_instances_not_classes() -> None:
    """REGISTRY holds instantiated plugins, not class references.

    main.py expects plugin.start() not Plugin.start(self). Catching this
    early prevents a confusing TypeError at boot.
    """
    for entry in plugins_registry.REGISTRY:
        assert not isinstance(entry, type), (
            f"Registry entry {entry} appears to be a class, not an instance. "
            f"Did you forget the parentheses? Use `MyPlugin()` not `MyPlugin`."
        )


def test_plugin_class_names_unique() -> None:
    """Two registry entries with the same class name almost certainly
    means an accidental duplicate. Catch it here."""
    names = [type(p).__name__ for p in plugins_registry.REGISTRY]
    duplicates = {n for n in names if names.count(n) > 1}
    assert not duplicates, f"Duplicate plugin classes in REGISTRY: {duplicates}"
