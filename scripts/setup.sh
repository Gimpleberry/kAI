#!/usr/bin/env bash
# =============================================================================
# kAI — local setup (cross-platform: Windows Git Bash, macOS, Linux)
# =============================================================================
# Usage: bash scripts/setup.sh
#
# Creates a venv, installs deps, validates config, initializes the data dir,
# and installs git hooks. Idempotent — safe to re-run.
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Detect platform — Windows behaves differently for venv paths and Python launcher
# -----------------------------------------------------------------------------
IS_WINDOWS=false
case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) IS_WINDOWS=true ;;
esac

# -----------------------------------------------------------------------------
# Find a working Python 3.12 interpreter
# -----------------------------------------------------------------------------
# Priority order:
#   1. py -3.12       (Windows Python launcher — most reliable on Windows)
#   2. python3.12     (explicit version on Linux/macOS)
#   3. python3        (generic Linux/macOS)
#   4. python         (last resort — Windows often only has this)
# We require 3.12.x specifically because dependencies are pinned for it.
# -----------------------------------------------------------------------------

PYTHON=""

# Try the Windows launcher first
if command -v py &> /dev/null; then
    if py -3.12 --version &> /dev/null; then
        PYTHON="py -3.12"
    fi
fi

# Try explicit python3.12 (common on Linux/macOS)
if [[ -z "$PYTHON" ]] && command -v python3.12 &> /dev/null; then
    PYTHON="python3.12"
fi

# Try generic python3 — but verify it's 3.12.x
if [[ -z "$PYTHON" ]] && command -v python3 &> /dev/null; then
    if python3 --version 2>&1 | grep -q "Python 3.12"; then
        PYTHON="python3"
    fi
fi

# Try bare python — also verify it's 3.12.x
if [[ -z "$PYTHON" ]] && command -v python &> /dev/null; then
    if python --version 2>&1 | grep -q "Python 3.12"; then
        PYTHON="python"
    fi
fi

if [[ -z "$PYTHON" ]]; then
    echo "ERROR: Python 3.12.x not found." >&2
    echo "" >&2
    echo "We require Python 3.12 specifically (not 3.13/3.14) because pinned" >&2
    echo "scientific dependencies don't have wheels for newer versions yet." >&2
    echo "" >&2
    echo "Install Python 3.12:" >&2
    echo "  Windows: winget install Python.Python.3.12 --source winget" >&2
    echo "  macOS:   brew install python@3.12" >&2
    echo "  Linux:   sudo apt install python3.12 (or your distro's equivalent)" >&2
    echo "" >&2
    exit 1
fi

PY_VERSION=$($PYTHON --version 2>&1)
echo "✓ Using $PYTHON — $PY_VERSION"

# -----------------------------------------------------------------------------
# Repo root + venv path (differs by platform)
# -----------------------------------------------------------------------------
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if $IS_WINDOWS; then
    VENV_ACTIVATE=".venv/Scripts/activate"
    VENV_PYTHON=".venv/Scripts/python.exe"
else
    VENV_ACTIVATE=".venv/bin/activate"
    VENV_PYTHON=".venv/bin/python"
fi

# -----------------------------------------------------------------------------
# Create venv if missing
# -----------------------------------------------------------------------------
if [[ ! -d .venv ]]; then
    echo "→ Creating virtualenv at .venv/"
    $PYTHON -m venv .venv
fi

# -----------------------------------------------------------------------------
# Activate and install — using the venv's Python directly is most reliable
# -----------------------------------------------------------------------------
# shellcheck source=/dev/null
source "$VENV_ACTIVATE"

echo "→ Installing dependencies (this may take a minute)..."
"$VENV_PYTHON" -m pip install --quiet --upgrade pip
"$VENV_PYTHON" -m pip install --quiet -e ".[dev]"

# -----------------------------------------------------------------------------
# Initialize .env if missing
# -----------------------------------------------------------------------------
if [[ ! -f .env ]]; then
    echo "→ Creating .env from .env.example"
    cp .env.example .env
fi

# -----------------------------------------------------------------------------
# Create data directory
# -----------------------------------------------------------------------------
mkdir -p data
echo "✓ Data directory ready at ./data/"

# -----------------------------------------------------------------------------
# Install git hooks if this is a git repo
# -----------------------------------------------------------------------------
if [[ -d .git ]]; then
    bash scripts/install_hooks.sh
else
    echo "  (Skipping git hooks — not a git repo yet. Run 'git init' then 'bash scripts/install_hooks.sh')"
fi

# -----------------------------------------------------------------------------
# Validate config and run tests
# -----------------------------------------------------------------------------
echo "→ Validating taxonomy..."
"$VENV_PYTHON" -m kai.cli validate-taxonomy

echo "→ Running tests..."
"$VENV_PYTHON" -m pytest tests/unit/ -q

# -----------------------------------------------------------------------------
# Final instructions — platform-specific activation hints
# -----------------------------------------------------------------------------
echo ""
echo "================================================================"
echo "  kAI setup complete."
echo ""
if $IS_WINDOWS; then
    echo "  To activate the venv in a new terminal session:"
    echo "    source .venv/Scripts/activate"
else
    echo "  To activate the venv in a new terminal session:"
    echo "    source .venv/bin/activate"
fi
echo ""
echo "  Then to start the API (once implemented):"
echo "    uvicorn kai.elicitation.api:create_app --factory --reload"
echo "================================================================"
