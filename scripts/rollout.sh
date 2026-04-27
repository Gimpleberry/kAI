#!/usr/bin/env bash
# =============================================================================
# kAI — Patch rollout workflow (11 steps)
# =============================================================================
# Per ARCHITECTURE_TENETS "Patch Rollout Process" / "Standard rollout workflow".
#
# This script walks you through the 11-step rollout for any meaningful change,
# stopping at each gate and waiting for confirmation. It does NOT do the work
# for you — it asks the right questions in the right order so nothing slips.
#
# Skip flag (--hotfix) skips PLAN/BRANCH/PR steps but enforces all QC steps.
# Per the tenet: "Speed kills less often than missed QC. The discipline that
# matters most is the discipline you keep when it's hardest."
#
# Usage:
#   bash scripts/rollout.sh                  # standard rollout
#   bash scripts/rollout.sh --hotfix         # hotfix shortcuts allowed
#   bash scripts/rollout.sh --dry-run        # show steps without prompting
# =============================================================================

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# -----------------------------------------------------------------------------
# Argument parsing
# -----------------------------------------------------------------------------
HOTFIX=false
DRY_RUN=false
for arg in "$@"; do
    case "$arg" in
        --hotfix) HOTFIX=true ;;
        --dry-run) DRY_RUN=true ;;
        --help|-h)
            sed -n '2,30p' "$0"
            exit 0
            ;;
        *) echo "Unknown flag: $arg" >&2; exit 2 ;;
    esac
done

# -----------------------------------------------------------------------------
# Output helpers
# -----------------------------------------------------------------------------
sep ()    { echo ""; echo "===================================================="; }
step ()   { sep; echo "STEP $1: $2"; sep; }
ok ()     { echo "  ✓ $*"; }
warn ()   { echo "  ⚠ $*"; }
fail ()   { echo "  ✗ $*"; exit 1; }
prompt () {
    if $DRY_RUN; then return 0; fi
    read -r -p "  ▶ $1 [y/N]: " ans
    case "$ans" in
        [yY]|[yY][eE][sS]) return 0 ;;
        *) return 1 ;;
    esac
}

# -----------------------------------------------------------------------------
# Detect Windows/venv path
# -----------------------------------------------------------------------------
IS_WINDOWS=false
case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) IS_WINDOWS=true ;;
esac
if $IS_WINDOWS; then VENV_PYTHON=".venv/Scripts/python.exe"
else VENV_PYTHON=".venv/bin/python"
fi
if [[ ! -x "$VENV_PYTHON" ]]; then
    fail "venv not found at $VENV_PYTHON. Run: bash scripts/setup.sh"
fi

# -----------------------------------------------------------------------------
echo ""
echo "kAI patch rollout"
$HOTFIX && echo "MODE: HOTFIX (PLAN/BRANCH/PR steps optional)"
$DRY_RUN && echo "MODE: DRY RUN (no prompts, no actions)"
echo ""

# -----------------------------------------------------------------------------
# 1. PLAN
# -----------------------------------------------------------------------------
step 1 "PLAN — write down WHAT and WHY"
echo "  This change should have a home in BACKLOG.md (or be a hotfix)."
echo ""
if ! $HOTFIX; then
    if ! prompt "Is the WHAT/WHY captured (BACKLOG entry, ADR, or issue)?"; then
        fail "Add a BACKLOG entry first, then re-run rollout."
    fi
else
    warn "Hotfix mode — backfilling BACKLOG/CHANGELOG is required by end of day."
fi
ok "Plan captured"

# -----------------------------------------------------------------------------
# 2. BRANCH
# -----------------------------------------------------------------------------
step 2 "BRANCH — feature branch, verb-first naming"
CUR_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
echo "  Current branch: $CUR_BRANCH"
if [[ "$CUR_BRANCH" == "main" || "$CUR_BRANCH" == "master" ]]; then
    if ! $HOTFIX; then
        warn "You're on $CUR_BRANCH. Recommended: branch with verb-first name."
        warn "  Examples: add-cbc-generator, fix-encoding-sweep, refactor-shared"
        if ! prompt "Continue on $CUR_BRANCH anyway?"; then
            fail "Create a feature branch first: git checkout -b <verb>-<description>"
        fi
    fi
fi
ok "Branch decision recorded"

# -----------------------------------------------------------------------------
# 3. IMPLEMENT (no automation here — you write the code)
# -----------------------------------------------------------------------------
step 3 "IMPLEMENT — write the code"
echo "  Reminders:"
echo "    - Single source of truth: cross-cutting symbols → src/kai/shared.py"
echo "    - Plugin pattern: feature module + line in plugins.py"
echo "    - Layered architecture: STORAGE → REFRESH → API → UI"
echo "    - REMOVE-AND-EXPLAIN: when removing code, leave a comment WHY"
prompt "Implementation done?" || fail "Resume rollout when implementation is done."
ok "Implementation"

# -----------------------------------------------------------------------------
# 4. SELF-REVIEW — run git diff
# -----------------------------------------------------------------------------
step 4 "SELF-REVIEW — read your own diff start to finish"
echo "  Look for:"
echo "    - Hardcoded values that belong in shared.py"
echo "    - Encoding issues (non-ASCII in Python source)"
echo "    - Missing stop() methods on new plugins"
echo "    - Copy-pasted code that should be DRY"
echo "    - Silent fallbacks (FAIL LOUD instead)"
echo ""
if ! $DRY_RUN; then
    git --no-pager diff --stat
    echo ""
    prompt "Diff reviewed end-to-end?" || fail "Review the diff before proceeding."
fi
ok "Self-review"

# -----------------------------------------------------------------------------
# 5. PRE-CHANGE VALIDATION CHECKLIST (10 items)
# -----------------------------------------------------------------------------
step 5 "VALIDATE — bash scripts/validate.sh (10-item Tenet 5 checklist)"
echo "  Hotfixes do NOT skip this. Per the tenet:"
echo "    'Speed kills less often than missed QC.'"
echo ""
if ! $DRY_RUN; then
    if ! bash scripts/validate.sh; then
        fail "Validation failed. Fix the failures listed above before continuing."
    fi
fi
ok "All 10 validation checks passed"

# -----------------------------------------------------------------------------
# 6. UPDATE DOCS
# -----------------------------------------------------------------------------
step 6 "UPDATE DOCS — three files always touched"
echo "  Required:"
echo "    - CHANGELOG.md       : add entry under appropriate version + tag(s)"
echo "    - PROJECT_KNOWLEDGE  : update if architecture or folder map changed"
echo "    - BACKLOG.md         : remove done item, add follow-ups"
echo "  Conditional:"
echo "    - DECISIONS.md       : add ADR if architectural choice involved"
echo "    - README.md          : update if operator-facing behavior changed"
echo "    - In-app help        : update if user-facing behavior changed"
echo ""
prompt "All applicable docs updated?" || fail "Update docs before committing."
ok "Documentation updated"

# -----------------------------------------------------------------------------
# 7. COMMIT — atomic, with WHAT and WHY
# -----------------------------------------------------------------------------
step 7 "COMMIT — atomic, message states WHAT and WHY"
echo "  Conventions:"
echo "    - One logical change per commit"
echo "    - First line: imperative + WHAT (e.g., 'Add CBC generator')"
echo "    - Body: WHY this change is needed (if non-obvious)"
echo "    - Reference backlog/issue: 'closes #42' or 'BACKLOG: Phase 1.2'"
echo ""
if ! $DRY_RUN; then
    git --no-pager status --short
    echo ""
    prompt "Have you staged and committed the changes?" || \
        fail "Commit before pushing."
fi
ok "Committed"

# -----------------------------------------------------------------------------
# 8. PRE-PUSH CHECKLIST
# -----------------------------------------------------------------------------
step 8 "PRE-PUSH — final pre-push gate"
echo "  Final scan for:"
echo "    - Accidental secrets in commit content"
echo "    - Personal data files (.db, .env, data/)"
echo "    - PII in commit messages"
echo ""
if ! $DRY_RUN; then
    # The pre-commit hook already blocks .db/.env staging, but confirm.
    if git --no-pager log --name-only HEAD~1..HEAD 2>/dev/null | \
            grep -E '(\.db$|\.env$|^data/)' >/dev/null; then
        fail "Recent commit appears to include personal data. Stop and audit."
    fi
fi
ok "Pre-push scan clean"

# -----------------------------------------------------------------------------
# 9. PR (skipped on hotfix)
# -----------------------------------------------------------------------------
step 9 "PR — fill the PR template, self-review counts on solo projects"
if $HOTFIX; then
    warn "Hotfix mode — PR can be opened post-merge for record-keeping."
else
    echo "  The PR template (.github/PULL_REQUEST_TEMPLATE.md) re-affirms:"
    echo "    - 10-item validation checklist"
    echo "    - Doc updates"
    echo "    - Risk + rollback plan"
    echo ""
    prompt "PR opened with template filled (or you're solo and self-reviewed)?" \
        || fail "Open the PR before merging to main."
fi
ok "PR step recorded"

# -----------------------------------------------------------------------------
# 10. MERGE & TAG
# -----------------------------------------------------------------------------
step 10 "MERGE & TAG — squash/rebase, tag the version"
echo "  Tag conventions (multi-tag allowed):"
echo "    Major | Feature | Fix | Security | Refactor"
echo "    Performance | Architecture | Scalability"
echo "  Format: v0.2.1, v0.3.0, v1.0.0 (major.minor[.patch])"
echo ""
prompt "Merged to main and tagged the release?" || \
    warn "Don't forget: git tag -a vX.Y.Z -m 'description' && git push --tags"
ok "Merge & tag step recorded"

# -----------------------------------------------------------------------------
# 11. POST-ROLLOUT VALIDATION
# -----------------------------------------------------------------------------
step 11 "POST-ROLLOUT — re-run validation on the deployed code"
echo "  On the operator's machine (your laptop), run:"
echo "    bash scripts/validate.sh"
echo "    python main.py --check"
echo ""
echo "  Confirm logs are clean. The patch is NOT done until this passes."
if ! $DRY_RUN; then
    if ! bash scripts/validate.sh fast; then
        warn "Post-rollout validation failed. Patch is not done."
        exit 1
    fi
fi
ok "Post-rollout validation"

# -----------------------------------------------------------------------------
sep
echo "  ✓ Rollout complete."
sep
exit 0
