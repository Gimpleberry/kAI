"""
shared.py — single source of truth for cross-cutting concerns.

Per ARCHITECTURE_TENETS Tenet 1: This is the ONLY place any cross-cutting
helper, constant, path, or error type may be defined. Every other module
IMPORTS from here. Nothing else redefines what this module owns.

Enforcement:
  - tests/unit/test_shared_uniqueness.py verifies no symbol exported here
    is redefined elsewhere in the codebase
  - The pre-commit hook runs that test before allowing a commit
  - Code review rule: if you find yourself duplicating a helper, promote
    it here on its second use

What belongs here:
  - All filesystem paths (REPO_ROOT, DATA_DIR, CONFIG_DIR, ...)
  - All cross-module constants (versions, thresholds, timeouts)
  - All cross-module helpers (config loading, batch isolation, logging)
  - All error types used in more than one module

What does NOT belong here:
  - Module-specific helpers used in exactly one module (keep local)
  - Constants that belong to a single module's internal logic
  - Anything coupled to a specific feature's data shapes
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

# =============================================================================
# Filesystem paths
# =============================================================================
# REPO_ROOT resolves to the directory that contains pyproject.toml. Computed
# once at import time. Every other module needing a path imports REPO_ROOT
# (or one of its derived paths) from here — no module should walk parents
# of __file__ on its own.

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
CONFIG_DIR: Path = REPO_ROOT / "config"
DATA_DIR: Path = REPO_ROOT / "data"
TESTS_DIR: Path = REPO_ROOT / "tests"
SCRIPTS_DIR: Path = REPO_ROOT / "scripts"
LOGS_DIR: Path = DATA_DIR / "logs"

TAXONOMY_PATH: Path = CONFIG_DIR / "taxonomy.yaml"
DESIGN_PARAMS_PATH: Path = CONFIG_DIR / "design_params.yaml"
ENV_FILE_PATH: Path = REPO_ROOT / ".env"

# =============================================================================
# Versions
# =============================================================================
# Application version is read from pyproject.toml at runtime; we don't
# duplicate it here. Tracked separately:

CBC_GENERATOR_VERSION: str = "1.0.0"
"""CBC design generator algorithm version. Bump when the generation algorithm
changes in a way that would produce different output for the same seed
(per ADR-005). Stored on each Session row for compatibility checking."""

MAXDIFF_GENERATOR_VERSION: str = "1.0.0"
"""MaxDiff design generator version. Same semantics as CBC_GENERATOR_VERSION."""

SCHEMA_VERSION: int = 1
"""Database schema version. Bump on breaking schema changes; Alembic
migrations handle the upgrade path."""

# =============================================================================
# Cross-cutting thresholds
# =============================================================================
# These are constants multiple modules need to agree on. Module-specific
# tuning parameters stay in design_params.yaml or each module's own constants.

MIN_OBS_PARAMS_RATIO: float = 5.0
"""Minimum observations-to-parameters ratio required for stable MNL
estimation. Validated at design generation and again at estimation entry."""

QUALITY_GATE_MIN_D_EFFICIENCY: float = 0.85
"""Minimum D-efficiency for a CBC design to pass quality gates."""

DEFAULT_LOG_MAX_BYTES: int = 5 * 1024 * 1024  # 5 MB per file
DEFAULT_LOG_BACKUP_COUNT: int = 3
"""Log rotation defaults — per the tenet: 'Disk-fill is a real failure mode
for 24/7 services.' These can be overridden per-logger if needed."""


# =============================================================================
# Error types
# =============================================================================
# Errors used in more than one module live here so callers can catch them
# without circular imports. Module-specific exceptions stay in those modules.


class KaiError(Exception):
    """Base for all kAI-specific errors. Catches everything we raise."""


class ConfigError(KaiError):
    """Raised when configuration is missing, malformed, or contradictory.

    Per Tenet 3: we FAIL LOUDLY rather than silently fall back to defaults.
    Anywhere config might be missing, raise this with a clear remediation
    message — never paper over with a default."""


class ValidationError(KaiError):
    """Raised when input fails validation. Distinct from Pydantic's
    ValidationError — we wrap or re-raise that as this when crossing
    module boundaries, so callers have one type to catch."""


class DataIntegrityError(KaiError):
    """Raised when persisted data violates an invariant the schema
    couldn't enforce (e.g., taxonomy_version mismatch when regenerating
    a design from a stored seed)."""


class QualityGateError(KaiError):
    """Raised when a quality gate (design D-efficiency, estimation
    convergence, etc.) fails. Carries a list of specific failed checks."""

    def __init__(self, message: str, failed_checks: list[str]) -> None:
        super().__init__(message)
        self.failed_checks = failed_checks


class ActionSafetyError(KaiError):
    """Raised when an irreversible-action guard rejects an attempted action.

    Per ADR-009 / ARCHITECTURE_TENETS Tenet 3 ("Action Safety"): code
    that performs irreversible actions (writes outside the local DB,
    sends external messages, mutates user-visible state) MUST validate
    intent before acting. This error indicates that validation failed
    and the action was deliberately not taken."""


# =============================================================================
# Config loading — single entry point
# =============================================================================
# Per Tenet 3: source code reads config via THIS function. Nowhere else
# in the codebase opens .env or design_params.yaml directly. If a value
# is missing, raise ConfigError loudly — no silent fallback to placeholders.


def load_local_config() -> dict[str, Any]:
    """Load environment configuration from .env (if present) plus os.environ.

    Returns a flat dict of KAI_* env vars (without the prefix). Order of
    precedence: actual environment > .env file > nothing (raise on access
    of a missing required key).

    Tenet 3 alignment: if .env is missing and KAI_DB_URL isn't set in the
    real environment, we still don't fall back silently — the caller will
    raise ConfigError when they try to read the missing key. This function
    just gathers what's available; validation is the caller's job.

    Raises:
        ConfigError: only if .env exists but is unreadable.
    """
    config: dict[str, Any] = {}

    # Layer 1: .env file (if present)
    if ENV_FILE_PATH.exists():
        try:
            for line in ENV_FILE_PATH.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key.startswith("KAI_"):
                    config[key.removeprefix("KAI_")] = value
        except OSError as e:
            raise ConfigError(
                f"Failed to read {ENV_FILE_PATH}: {e}. "
                f"Either fix permissions or remove the file to use os.environ only."
            ) from e

    # Layer 2: os.environ (overrides .env)
    for env_key, env_value in os.environ.items():
        if env_key.startswith("KAI_"):
            config[env_key.removeprefix("KAI_")] = env_value

    return config


def get_config_value(key: str, default: Any = ...) -> Any:
    """Fetch a single config value by key (without KAI_ prefix).

    If the key is absent and no default is provided, raise ConfigError
    rather than returning None — failing loudly per Tenet 3.

    Args:
        key: The config key, without the KAI_ prefix (e.g., "DB_URL").
        default: If provided, returned when key is absent. Use the sentinel
            `...` (or omit) to require the key.

    Raises:
        ConfigError: If key absent and no default provided.
    """
    config = load_local_config()
    if key in config:
        return config[key]
    if default is ...:
        raise ConfigError(
            f"Required config key 'KAI_{key}' is not set. "
            f"Add it to {ENV_FILE_PATH} or export it in your environment. "
            f"See .env.example for the full list of required keys."
        )
    return default


# =============================================================================
# Per-item exception isolation (Resilience pattern)
# =============================================================================
# Per ARCHITECTURE_TENETS "Resilience & fault isolation" / Anti-pattern
# "I'll add tests later" sibling pattern: in any batch operation, ONE bad
# item must NOT abort the entire run.
#
# This is going to matter immediately for Phase 1 (CBC bootstrap iterations
# and per-attribute estimation). Putting it in shared NOW so the pattern
# is uniform across every batch loop in the codebase.

T = TypeVar("T")
R = TypeVar("R")


@dataclass(frozen=True)
class BatchResult:
    """Counts + collected results from a per-item-isolated batch operation.

    Returned by batch_with_isolation. The counts dict serves as the
    audit-trail log line per the tenet: "The counts log line IS the
    audit trail."
    """

    total: int
    ok: int
    failed: int
    skipped: int
    results: list[Any]
    errors: list[tuple[Any, Exception]]
    """List of (item, exception) tuples for items that raised. Empty if
    no failures. Useful for re-running just the failures or for surfacing
    them in a diagnostic UI."""

    def summary(self) -> str:
        """One-line summary suitable for the trailing log message."""
        return (
            f"batch complete: total={self.total} ok={self.ok} "
            f"failed={self.failed} skipped={self.skipped}"
        )


class SkipItem(Exception):  # noqa: N818
    """Sentinel exception. Raise inside a batch_with_isolation process_fn
    to skip the current item without counting it as a failure (counts as
    'skipped', not 'failed').

    Named without an 'Error' suffix because this is a control-flow signal,
    not an error condition — hence the N818 noqa."""


def batch_with_isolation(
    items: Iterable[T],
    process_fn: Callable[[T], R],
    logger: logging.Logger | None = None,
    description: str = "batch",
) -> BatchResult:
    """Run process_fn over each item, isolating failures.

    One bad item never aborts the run. Failures are logged at WARNING,
    skips at DEBUG, and the final counts are logged at INFO. The
    BatchResult contains the successful results plus an errors list
    of (item, exception) tuples for any item that raised.

    Use it for:
      - Bootstrap iterations in MNL estimation
      - Per-attribute computations in design diagnostics
      - Per-session profile regenerations
      - Any future scrape/refresh loop

    Don't use it for:
      - Operations that should be all-or-nothing (DB transactions,
        atomic writes — those want a try/except and rollback, not isolation)

    Args:
        items: An iterable of items to process.
        process_fn: A callable taking one item and returning a result.
            Raise SkipItem to skip without counting as failure.
            Any other exception is caught and logged.
        logger: Logger to use. Defaults to a "kai.batch" logger.
        description: Used in log messages to identify which batch this is.

    Returns:
        A BatchResult with counts, results, and errors.
    """
    log = logger or logging.getLogger("kai.batch")
    total = ok = failed = skipped = 0
    results: list[Any] = []
    errors: list[tuple[Any, Exception]] = []

    for item in items:
        total += 1
        try:
            result = process_fn(item)
            results.append(result)
            ok += 1
        except SkipItem as e:
            skipped += 1
            log.debug("[%s] skipped item %r: %s", description, item, e)
        except Exception as e:  # noqa: BLE001 — we deliberately want broad catch
            failed += 1
            errors.append((item, e))
            log.warning(
                "[%s] item %r failed: %s: %s",
                description,
                item,
                type(e).__name__,
                e,
            )

    result_obj = BatchResult(
        total=total,
        ok=ok,
        failed=failed,
        skipped=skipped,
        results=results,
        errors=errors,
    )
    log.info("[%s] %s", description, result_obj.summary())
    return result_obj


# =============================================================================
# Logging — masking + rotation
# =============================================================================
# Per ARCHITECTURE_TENETS "Observability & debug modes":
#   - Never log a secret in full.
#   - Apply masking inside the function that DOES the logging — don't
#     rely on every caller to remember.
#   - Logs ROTATE at a size limit. Disk-fill is a real failure mode.

# Patterns that look like secrets — used by mask_secret to pick the
# preserved-length suffix automatically.
_SECRET_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,}$")


def mask_secret(value: str | None, *, keep_chars: int = 4) -> str:
    """Mask a value for safe logging. Returns 'tcg-****xd3h'-style strings.

    Behavior:
      - None or empty → "<unset>"
      - Length <= keep_chars*2 → returned as "<masked>" with no leak
      - Otherwise → first 0 chars + "****" + last keep_chars chars

    This is the helper to use anywhere a config value, token, ID, or
    URL with embedded credentials might end up in a log line.

    Args:
        value: The value to mask. Anything stringable.
        keep_chars: How many trailing characters to preserve. Defaults
            to 4, which is enough to disambiguate values for debugging
            without leaking them.
    """
    if value is None or value == "":
        return "<unset>"
    s = str(value)
    if len(s) <= keep_chars * 2:
        return "<masked>"
    return f"****{s[-keep_chars:]}"


def setup_rotating_logger(
    name: str,
    *,
    log_file: Path | None = None,
    level: int = logging.INFO,
    max_bytes: int = DEFAULT_LOG_MAX_BYTES,
    backup_count: int = DEFAULT_LOG_BACKUP_COUNT,
    console: bool = True,
) -> logging.Logger:
    """Configure a logger with rotating file output + optional console.

    The file goes to data/logs/<name>.log by default and rotates at
    max_bytes, keeping backup_count old files (e.g., name.log.1 ... .3).

    Plugins should call this once in their start() method with their own
    logger name; subsequent calls with the same name are idempotent
    (handlers aren't duplicated).

    Args:
        name: Logger name (e.g., "kai.elicitation.api").
        log_file: Path to the log file. Defaults to LOGS_DIR / f"{name}.log".
        level: Log level (logging.INFO, etc.).
        max_bytes: File size at which to rotate.
        backup_count: How many rotated files to keep.
        console: If True, also emit to stderr.

    Returns:
        The configured logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Idempotency: don't add the same handler twice across plugin restarts
    handler_keys = {(type(h).__name__, getattr(h, "baseFilename", None)) for h in logger.handlers}

    target = log_file or (LOGS_DIR / f"{name}.log")
    target.parent.mkdir(parents=True, exist_ok=True)

    fh_key = ("RotatingFileHandler", str(target))
    if fh_key not in handler_keys:
        fh = logging.handlers.RotatingFileHandler(
            target, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        fh.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        logger.addHandler(fh)

    if console:
        ch_key = ("StreamHandler", None)
        if ch_key not in handler_keys:
            ch = logging.StreamHandler()
            ch.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%H:%M:%S",
                )
            )
            logger.addHandler(ch)

    return logger


# =============================================================================
# Public API — what other modules may import from shared
# =============================================================================
# Symbols listed here are the exported surface. The uniqueness check in
# tests/unit/test_shared_uniqueness.py verifies these aren't redefined
# anywhere else in the codebase.

__all__ = [
    # Paths
    "REPO_ROOT",
    "CONFIG_DIR",
    "DATA_DIR",
    "TESTS_DIR",
    "SCRIPTS_DIR",
    "LOGS_DIR",
    "TAXONOMY_PATH",
    "DESIGN_PARAMS_PATH",
    "ENV_FILE_PATH",
    # Versions
    "CBC_GENERATOR_VERSION",
    "MAXDIFF_GENERATOR_VERSION",
    "SCHEMA_VERSION",
    # Thresholds + log defaults
    "MIN_OBS_PARAMS_RATIO",
    "QUALITY_GATE_MIN_D_EFFICIENCY",
    "DEFAULT_LOG_MAX_BYTES",
    "DEFAULT_LOG_BACKUP_COUNT",
    # Errors
    "KaiError",
    "ConfigError",
    "ValidationError",
    "DataIntegrityError",
    "QualityGateError",
    "ActionSafetyError",
    # Config loading
    "load_local_config",
    "get_config_value",
    # Batch isolation
    "BatchResult",
    "SkipItem",
    "batch_with_isolation",
    # Logging
    "mask_secret",
    "setup_rotating_logger",
]
