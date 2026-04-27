"""
Tests for main.py lifecycle orchestration.

Per ARCHITECTURE_TENETS "Graceful Shutdown" section:
  - stop() runs in REVERSE boot order
  - Even if start() partially failed, stop() runs on all started plugins
  - One plugin's stop() raising must NOT prevent later stops

These tests use synthetic Plugin instances rather than the real registry,
so they don't depend on storage/taxonomy/etc actually being installed.
"""

from __future__ import annotations

import pytest

import main


class _RecordingPlugin:
    """Test double that records start()/stop() calls into a shared log."""

    def __init__(
        self,
        name: str,
        *,
        fail_start: bool = False,
        fail_stop: bool = False,
        log: list[str] | None = None,
    ) -> None:
        self.name = name
        self.fail_start = fail_start
        self.fail_stop = fail_stop
        self._log = log if log is not None else []

    def __repr__(self) -> str:
        return f"_RecordingPlugin({self.name!r})"

    def start(self) -> None:
        self._log.append(f"start:{self.name}")
        if self.fail_start:
            raise RuntimeError(f"simulated start failure in {self.name}")

    def stop(self) -> None:
        self._log.append(f"stop:{self.name}")
        if self.fail_stop:
            raise RuntimeError(f"simulated stop failure in {self.name}")


def test_stop_runs_in_reverse_order() -> None:
    log: list[str] = []
    plugins = [_RecordingPlugin(n, log=log) for n in ("A", "B", "C")]
    started = main._start_all(plugins)
    main._stop_all(started)

    assert log == [
        "start:A",
        "start:B",
        "start:C",  # boot order
        "stop:C",
        "stop:B",
        "stop:A",  # reverse order
    ]


def test_partial_start_failure_only_stops_started_plugins() -> None:
    """If C raises during start(), B and A should be stopped (in reverse),
    and C should NOT have stop() called because its start() didn't complete."""
    log: list[str] = []
    plugins = [
        _RecordingPlugin("A", log=log),
        _RecordingPlugin("B", log=log),
        _RecordingPlugin("C", log=log, fail_start=True),
    ]

    with pytest.raises(RuntimeError, match="simulated start failure in C"):
        main._start_all(plugins)

    # _start_all returns nothing on raise, so we manually inspect the log
    # to confirm the right plugins started
    assert log == ["start:A", "start:B", "start:C"]

    # In real usage, main() catches the exception and calls _stop_all on
    # whatever did start. Simulate that by passing only A and B.
    started = [plugins[0], plugins[1]]
    main._stop_all(started)
    assert log == [
        "start:A",
        "start:B",
        "start:C",
        "stop:B",
        "stop:A",  # only the started plugins, in reverse
    ]


def test_stop_continues_after_individual_stop_failure() -> None:
    """If B's stop() raises, A's stop() must still run.

    This is the 'best-effort shutdown' contract from main._stop_all.
    """
    log: list[str] = []
    plugins = [
        _RecordingPlugin("A", log=log),
        _RecordingPlugin("B", log=log, fail_stop=True),
        _RecordingPlugin("C", log=log),
    ]
    started = main._start_all(plugins)

    # Should NOT raise, despite B's stop() failing
    main._stop_all(started)

    assert "stop:A" in log
    assert "stop:B" in log
    assert "stop:C" in log
    # And in the right order: C, then B (which raised), then A
    stops_only = [e for e in log if e.startswith("stop:")]
    assert stops_only == ["stop:C", "stop:B", "stop:A"]


def test_check_plugins_passes_with_real_registry() -> None:
    """The real plugins.REGISTRY should pass the lifecycle check.

    This is the test that catches 'someone added a plugin without start/stop'.
    """
    rc = main._check_plugins()
    assert rc == 0, "main._check_plugins() returned nonzero — plugin lifecycle violation"
