"""
Tests for the resilience and observability helpers added in v0.2.1.
Covers batch_with_isolation, mask_secret, setup_rotating_logger.
"""

from __future__ import annotations

import logging
import tempfile
from contextlib import contextmanager
from pathlib import Path

from kai.shared import (
    BatchResult,
    SkipItem,
    batch_with_isolation,
    mask_secret,
    setup_rotating_logger,
)

# =============================================================================
# Test helper: managed logger that releases its handlers on exit
# =============================================================================
# Windows refuses to delete a directory that has an open file handle in it.
# RotatingFileHandler keeps the log file open for the lifetime of the handler.
# This context manager closes and removes file handlers after the test, so
# tempfile.TemporaryDirectory can clean up cleanly.

@contextmanager
def _managed_logger(name: str, **kwargs):
    """Yield a logger configured via setup_rotating_logger; close + detach
    its file handlers on exit."""
    logger = setup_rotating_logger(name, **kwargs)
    try:
        yield logger
    finally:
        # Close every handler and remove it from the logger so subsequent
        # tempdir cleanup doesn't trip on a held file handle (Windows).
        for handler in list(logger.handlers):
            try:
                handler.flush()
                handler.close()
            except Exception:
                pass
            logger.removeHandler(handler)


# =============================================================================
# batch_with_isolation
# =============================================================================


class TestBatchIsolation:
    def test_all_succeed(self) -> None:
        result = batch_with_isolation([1, 2, 3], lambda x: x * 2)
        assert result.total == 3
        assert result.ok == 3
        assert result.failed == 0
        assert result.skipped == 0
        assert result.results == [2, 4, 6]
        assert result.errors == []

    def test_some_fail_others_succeed(self) -> None:
        def process(x: int) -> int:
            if x == 2:
                raise ValueError("boom")
            return x * 10

        result = batch_with_isolation([1, 2, 3, 4], process)
        assert result.total == 4
        assert result.ok == 3
        assert result.failed == 1
        assert result.skipped == 0
        assert result.results == [10, 30, 40]
        assert len(result.errors) == 1
        item, exc = result.errors[0]
        assert item == 2
        assert isinstance(exc, ValueError)

    def test_skip_item_does_not_count_as_failure(self) -> None:
        def process(x: int) -> int:
            if x % 2 == 0:
                raise SkipItem(f"skipping even {x}")
            return x

        result = batch_with_isolation([1, 2, 3, 4, 5], process)
        assert result.total == 5
        assert result.ok == 3       # 1, 3, 5
        assert result.skipped == 2  # 2, 4
        assert result.failed == 0
        assert result.results == [1, 3, 5]

    def test_one_failing_item_does_not_abort(self) -> None:
        """Tenet check: one bad item must NEVER abort the batch."""
        processed: list[int] = []

        def process(x: int) -> int:
            processed.append(x)
            if x == 50:
                raise RuntimeError("simulated catastrophic failure")
            return x

        result = batch_with_isolation(range(100), process)
        assert processed == list(range(100))
        assert result.total == 100
        assert result.ok == 99
        assert result.failed == 1

    def test_summary_string(self) -> None:
        result = BatchResult(
            total=10, ok=8, failed=1, skipped=1,
            results=[], errors=[],
        )
        assert "total=10" in result.summary()
        assert "ok=8" in result.summary()
        assert "failed=1" in result.summary()
        assert "skipped=1" in result.summary()

    def test_empty_iterable(self) -> None:
        result = batch_with_isolation([], lambda x: x)
        assert result.total == 0
        assert result.ok == 0


# =============================================================================
# mask_secret
# =============================================================================


class TestMaskSecret:
    def test_none_returns_unset_marker(self) -> None:
        assert mask_secret(None) == "<unset>"

    def test_empty_string_returns_unset_marker(self) -> None:
        assert mask_secret("") == "<unset>"

    def test_short_value_fully_masked(self) -> None:
        assert mask_secret("abc") == "<masked>"
        assert mask_secret("12345678") == "<masked>"

    def test_long_value_keeps_tail(self) -> None:
        out = mask_secret("sk-abcdef1234567890xyz")
        assert out == "****0xyz"

    def test_custom_keep_chars(self) -> None:
        out = mask_secret("supersecrettoken-1234567890", keep_chars=6)
        assert out == "****567890"

    def test_no_leak_in_short_path(self) -> None:
        """Short values must NOT leak any characters at all.

        Regression guard: if someone changes the implementation to e.g.
        '****' + last char even when length is small, we'd leak the
        last char of a 5-char token.
        """
        for s in ["a", "ab", "abc", "abcd", "abcde", "abcdef", "abcdefg",
                  "abcdefgh"]:
            assert mask_secret(s) == "<masked>", \
                f"Short value {s!r} leaked: got {mask_secret(s)!r}"


# =============================================================================
# setup_rotating_logger
# =============================================================================
# Windows note: each test uses _managed_logger() so its file handlers are
# closed before tempfile.TemporaryDirectory tries to remove the directory.
# Without this, Windows raises PermissionError [WinError 32].


class TestSetupRotatingLogger:
    def test_writes_to_specified_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "test.log"
            with _managed_logger(
                "test_logger_unique_a", log_file=log_path, console=False
            ) as logger:
                logger.info("hello world")
                for h in logger.handlers:
                    h.flush()

                assert log_path.exists()
                content = log_path.read_text()
                assert "hello world" in content
                assert "INFO" in content

    def test_idempotent_setup(self) -> None:
        """Calling setup twice with the same args should not duplicate handlers."""
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "test.log"
            with _managed_logger(
                "test_logger_unique_b", log_file=log_path, console=False
            ) as logger:
                n_handlers_first = len(logger.handlers)

                # Second call returns the same logger; should not double-add.
                logger2 = setup_rotating_logger(
                    "test_logger_unique_b", log_file=log_path, console=False
                )
                n_handlers_second = len(logger2.handlers)

                assert n_handlers_first == n_handlers_second, (
                    "Calling setup_rotating_logger twice duplicated handlers"
                )

    def test_rotation_caps_file_size(self) -> None:
        """Confirm the rotation kicks in at the configured size."""
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "test.log"
            with _managed_logger(
                "test_logger_unique_c",
                log_file=log_path,
                console=False,
                max_bytes=200,
                backup_count=2,
            ) as logger:
                for i in range(50):
                    logger.info("filler line %d %s", i, "x" * 30)
                for h in logger.handlers:
                    h.flush()

                assert log_path.exists()
                assert log_path.stat().st_size < 500, (
                    f"Log file did not rotate; size={log_path.stat().st_size}"
                )


# =============================================================================
# Integration: real-world scenario for batch + masking + logging
# =============================================================================


def test_batch_with_secret_in_error_message_uses_masking(caplog) -> None:
    """A failure that mentions a secret should not leak it if the caller
    wraps the logged exception with mask_secret. This is documentation
    of the expected pattern, not enforcement — but the pattern needs
    to demonstrably work."""
    secret = "sk-abcdef1234567890xyz"

    def process(item: str) -> str:
        if item == "bad":
            raise ValueError(f"upstream rejected token {mask_secret(secret)}")
        return item

    with caplog.at_level(logging.WARNING, logger="kai.batch"):
        result = batch_with_isolation(["good", "bad"], process)

    assert result.failed == 1
    log_text = " ".join(rec.message for rec in caplog.records)
    assert "****0xyz" in log_text
    assert secret not in log_text
