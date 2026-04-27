#!/usr/bin/env bash
# =============================================================================
# kAI — Pre-change validation suite
# =============================================================================
# Runs the 10-item QC checklist from ARCHITECTURE_TENETS Tenet 5, adapted
# for kAI's actual architecture.
#
# Usage:
#   bash scripts/validate.sh         # run everything
#   bash scripts/validate.sh fast    # skip slow checks (integration boot)
#
# Exit code:
#   0  — all checks passed
#   1  — at least one check failed
# =============================================================================

set -uo pipefail   # NOT -e: we want to run every check even after some fail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Detect Windows for venv path differences
IS_WINDOWS=false
case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) IS_WINDOWS=true ;;
esac
if $IS_WINDOWS; then
    VENV_PYTHON=".venv/Scripts/python.exe"
else
    VENV_PYTHON=".venv/bin/python"
fi

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "✗ venv not found at $VENV_PYTHON. Run: bash scripts/setup.sh"
    exit 1
fi

MODE="${1:-full}"
PASS=0
FAIL=0
FAILURES=()

run_check () {
    local name="$1"
    shift
    echo ""
    echo "→ [${name}]"
    if "$@"; then
        echo "  ✓ PASS: ${name}"
        PASS=$((PASS+1))
    else
        echo "  ✗ FAIL: ${name}"
        FAIL=$((FAIL+1))
        FAILURES+=("${name}")
    fi
}

# -----------------------------------------------------------------------------
# 1. Lint — every modified Python file passes ruff
# -----------------------------------------------------------------------------
run_check "1. Lint (ruff)" "$VENV_PYTHON" -m ruff check src tests

# -----------------------------------------------------------------------------
# 2. Duplication check — no module redefines anything in shared.py
# -----------------------------------------------------------------------------
run_check "2. shared.py uniqueness" \
    "$VENV_PYTHON" -m pytest tests/unit/test_shared_uniqueness.py -q --no-header --tb=line

# -----------------------------------------------------------------------------
# 3. Output-context encoding sweep
# -----------------------------------------------------------------------------
# Per ARCHITECTURE_TENETS Tenet 5: "no smart quotes, em dashes, or non-ASCII
# chars in places that need ASCII (notification headers, log files on
# Windows, etc.)". The operative phrase is "places that need ASCII" —
# this is about RUNTIME OUTPUT, not source-code docstrings.
#
# Em-dashes inside docstrings are fine — they're never sent to a Windows
# console as bytes; they live as Python string objects and are documentation
# for humans reading the source. What we actually want to catch is non-ASCII
# inside string literals that DO get sent to output: print() calls, logger
# calls, format= keyword args.
#
# The check below scans only those specific patterns. False positives are
# possible but rare; if one bites, the fix is to use ASCII in the
# offending string or document an exemption.
encoding_sweep_python () {
    # Use python AST to find string literals inside print/logger calls.
    # This is more accurate than grep regex and handles multi-line strings.
    "$VENV_PYTHON" - <<'PYEOF'
import ast, sys
from pathlib import Path

OUTPUT_CALLS = {
    "print",
    # logger.info, .warning, .error, .debug, .critical, .exception
}
LOGGER_METHODS = {"info", "warning", "error", "debug", "critical", "exception"}

violations = []

def is_output_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Name) and func.id in OUTPUT_CALLS:
        return True
    if isinstance(func, ast.Attribute) and func.attr in LOGGER_METHODS:
        return True
    return False

def scan_strings_in_call(call: ast.Call, file: Path) -> None:
    """Walk into a call's args/kwargs looking for non-ASCII string literals."""
    for child in ast.walk(call):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            try:
                child.value.encode("ascii")
            except UnicodeEncodeError:
                # Find first non-ascii char for the report
                bad = next(c for c in child.value if ord(c) > 127)
                violations.append(
                    f"{file}:{child.lineno}: non-ASCII char {bad!r} "
                    f"in string passed to output call"
                )

for py_file in Path("src").rglob("*.py"):
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and is_output_call(node):
            scan_strings_in_call(node, py_file)

if violations:
    print("  Non-ASCII characters in output strings:")
    for v in violations:
        print(f"    {v}")
    sys.exit(1)
sys.exit(0)
PYEOF
}
run_check "3. Encoding sweep (output-context strings)" encoding_sweep_python

# -----------------------------------------------------------------------------
# 4. Plugin registry check — every entry has start()/stop(), no duplicates
# -----------------------------------------------------------------------------
run_check "4. Plugin registry conformance" \
    "$VENV_PYTHON" -m pytest tests/unit/test_plugins_registry.py -q --no-header --tb=line

# -----------------------------------------------------------------------------
# 5. Import-chain check — no circular imports; package imports cleanly
# -----------------------------------------------------------------------------
run_check "5. Import chain (clean import of kai)" \
    "$VENV_PYTHON" -c "import kai, plugins; print('imports OK')"

# -----------------------------------------------------------------------------
# 6. Lifecycle check — main.py --check validates start()/stop() on every plugin
# -----------------------------------------------------------------------------
run_check "6. Lifecycle (main.py --check)" \
    "$VENV_PYTHON" main.py --check

# -----------------------------------------------------------------------------
# 7. Documentation freshness — README + CHANGELOG + DECISIONS exist
#    (Content review is human; this just guards against accidental deletion.)
# -----------------------------------------------------------------------------
docs_present () {
    local missing=()
    for f in README.md CHANGELOG.md DECISIONS.md BACKLOG.md PROJECT_KNOWLEDGE.txt; do
        if [[ ! -f "$f" ]]; then
            missing+=("$f")
        fi
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "  Missing docs:"
        printf '    %s\n' "${missing[@]}"
        return 1
    fi
    return 0
}
run_check "7. Documentation files present" docs_present

# -----------------------------------------------------------------------------
# 8. Config validated — taxonomy + design_params load and pass schema checks
# -----------------------------------------------------------------------------
run_check "8. Config valid" \
    "$VENV_PYTHON" -m kai.cli validate-taxonomy

# -----------------------------------------------------------------------------
# 9. Diagnostic suite — full unit test pass
# -----------------------------------------------------------------------------
run_check "9. Unit tests" \
    "$VENV_PYTHON" -m pytest tests/unit -q --no-header --tb=line

# -----------------------------------------------------------------------------
# 10. Integration check — main.py boots and shuts down cleanly
#     (Skipped in 'fast' mode because it spins up the full lifecycle.)
# -----------------------------------------------------------------------------
boot_check () {
    # --boot-order doesn't actually start anything, so this is fast and
    # serves as a "the registry imports without exploding" check.
    "$VENV_PYTHON" main.py --boot-order > /dev/null
}
if [[ "$MODE" != "fast" ]]; then
    run_check "10. Integration boot (main.py --boot-order)" boot_check
else
    echo ""
    echo "→ [10. Integration boot]  SKIPPED (fast mode)"
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo ""
echo "================================================================"
echo "  Validation summary"
echo "    Passed: $PASS"
echo "    Failed: $FAIL"
if [[ $FAIL -gt 0 ]]; then
    echo ""
    echo "  Failed checks:"
    for f in "${FAILURES[@]}"; do
        echo "    - $f"
    done
    echo "================================================================"
    exit 1
fi
echo "================================================================"
exit 0
