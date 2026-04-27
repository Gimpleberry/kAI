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
  - All cross-module helper functions (parsers, formatters, notifiers)
  - All config-loading entry points (load_local_config, get_secret_X)
  - All error types used in more than one place

What does NOT belong here:
  - Module-specific helpers used in exactly one module (keep local)
  - Constants that belong to a single module's internal logic
  - Anything coupled to a specific feature's data shapes
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

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
    convergence, etc.) fails. Carries a list of specific failed checks.

    Renamed from QualityGateFailure in v0.2.0a per ruff N818
    (exception class names should end with 'Error')."""

    def __init__(self, message: str, failed_checks: list[str]) -> None:
        super().__init__(message)
        self.failed_checks = failed_checks


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
            for raw_line in ENV_FILE_PATH.read_text().splitlines():
                line = raw_line.strip()
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
    "TAXONOMY_PATH",
    "DESIGN_PARAMS_PATH",
    "ENV_FILE_PATH",
    # Versions
    "CBC_GENERATOR_VERSION",
    "MAXDIFF_GENERATOR_VERSION",
    "SCHEMA_VERSION",
    # Thresholds
    "MIN_OBS_PARAMS_RATIO",
    "QUALITY_GATE_MIN_D_EFFICIENCY",
    # Errors
    "KaiError",
    "ConfigError",
    "ValidationError",
    "DataIntegrityError",
    "QualityGateError",
    # Config loading
    "load_local_config",
    "get_config_value",
]
