"""Inherent diagnostic test: validate.sh and CI lint workflow stay in sync.

Why this test exists
--------------------
During Phase 1.1 and 1.2 rollouts, two PRs passed `bash scripts/validate.sh`
locally with 10 / 10 but were rejected by CI because the local gate did not
run `ruff format --check` while CI did. Per ARCHITECTURE_TENETS Tenet 5
("priority QC over speed") and the kAI rollout discipline, the local
validation gate must be a strict superset of what CI enforces, so a clean
local run is sufficient confidence to push.

This test guards the invariant going forward. If somebody removes a ruff
step from `scripts/validate.sh` without removing the matching one in CI
(or vice versa), this test fires with a message explaining the parity
contract.

What this test checks
---------------------
1. `scripts/validate.sh` invokes `ruff check src tests`.
2. `scripts/validate.sh` invokes `ruff format --check src tests`.
3. `.github/workflows/lint.yml` invokes `ruff check src tests`.
4. `.github/workflows/lint.yml` invokes `ruff format --check src tests`.

What this test deliberately does NOT check
------------------------------------------
- The exact Python invocation prefix (e.g. `$VENV_PYTHON -m`). The
  validate.sh form differs from CI which uses a system ruff install;
  that is intentional and orthogonal to lint parity.
- Other CI workflows (ci.yml, secret-scan.yml). Each workflow that has
  a local mirror should grow its own parity test as the project adds
  them. Captured in BACKLOG as a generalization opportunity.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kai.shared import REPO_ROOT

VALIDATE_SH = REPO_ROOT / "scripts" / "validate.sh"
LINT_YML = REPO_ROOT / ".github" / "workflows" / "lint.yml"

REQUIRED_INVOCATIONS = (
    "ruff check src tests",
    "ruff format --check src tests",
)


def _read(path: Path) -> str:
    if not path.exists():
        pytest.fail(
            f"Expected file does not exist: {path}. "
            f"This test asserts the kAI repo layout invariant."
        )
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("invocation", REQUIRED_INVOCATIONS)
def test_validate_sh_runs_ruff_invocation(invocation: str) -> None:
    """validate.sh item #1 must run both ruff check and ruff format --check.

    If this fails after a refactor of validate.sh, you almost certainly
    want to put the missing invocation back. The local gate is supposed
    to be a strict superset of CI - a clean local 10 / 10 must imply
    a clean CI lint job.
    """
    content = _read(VALIDATE_SH)
    assert invocation in content, (
        f"scripts/validate.sh is missing required invocation: {invocation!r}. "
        f"This invariant exists because CI runs this exact command in "
        f".github/workflows/lint.yml. If the local gate stops running it, "
        f"local validation no longer protects against CI failure. "
        f"If you intentionally removed this from validate.sh, also remove "
        f"the matching step from lint.yml AND update this test."
    )


@pytest.mark.parametrize("invocation", REQUIRED_INVOCATIONS)
def test_lint_yml_runs_ruff_invocation(invocation: str) -> None:
    """CI lint workflow must run both ruff check and ruff format --check.

    The same invariant as the validate.sh test, mirrored on the CI side.
    Together the two parametrized tests assert: every required ruff
    invocation appears in BOTH places.
    """
    content = _read(LINT_YML)
    assert invocation in content, (
        f".github/workflows/lint.yml is missing required invocation: "
        f"{invocation!r}. If you intentionally removed this from CI, also "
        f"remove the matching step from scripts/validate.sh AND update "
        f"this test."
    )


def test_validate_sh_and_lint_yml_target_same_paths() -> None:
    """Both gates must lint the same source paths (`src` and `tests`).

    Catches a subtle drift mode where one gate is updated to add or
    drop a path (e.g. someone adds `scripts/` to CI but not to local).
    The check is intentionally narrow - just confirms both files
    mention `src tests` in their ruff invocations.
    """
    validate_text = _read(VALIDATE_SH)
    lint_text = _read(LINT_YML)
    for path_phrase in ("ruff check src tests", "ruff format --check src tests"):
        assert path_phrase in validate_text, f"validate.sh missing path phrase: {path_phrase!r}"
        assert path_phrase in lint_text, f"lint.yml missing path phrase: {path_phrase!r}"
