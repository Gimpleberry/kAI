#!/usr/bin/env bash
# =============================================================================
# kAI — local setup
# =============================================================================
# Usage: bash scripts/setup.sh
#
# Creates a venv, installs deps, validates config, initializes the data dir,
# and installs git hooks. Idempotent — safe to re-run.
# =============================================================================

set -euo pipefail

# Detect Python — require 3.11+
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Install Python 3.11 or later." >&2
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [[ "$PY_MAJOR" -lt 3 ]] || ([[ "$PY_MAJOR" -eq 3 ]] && [[ "$PY_MINOR" -lt 11 ]]); then
    echo "ERROR: Python 3.11+ required, found $PY_VERSION" >&2
    exit 1
fi

echo "✓ Python $PY_VERSION"

# Repo root (parent of scripts/)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Create venv if missing
if [[ ! -d .venv ]]; then
    echo "→ Creating virtualenv at .venv/"
    python3 -m venv .venv
fi

# shellcheck source=/dev/null
source .venv/bin/activate

# Upgrade pip and install
echo "→ Installing dependencies (this may take a minute)..."
pip install --quiet --upgrade pip
pip install --quiet -e ".[dev]"

# Initialize .env if missing
if [[ ! -f .env ]]; then
    echo "→ Creating .env from .env.example"
    cp .env.example .env
fi

# Create data directory
mkdir -p data
echo "✓ Data directory ready at ./data/"

# Install git hooks if this is a git repo
if [[ -d .git ]]; then
    bash scripts/install_hooks.sh
else
    echo "  (Skipping git hooks — not a git repo yet. Run 'git init' then 'bash scripts/install_hooks.sh')"
fi

# Validate the taxonomy config
echo "→ Validating taxonomy..."
python3 -m kai.cli validate-taxonomy

# Run the unit tests
echo "→ Running tests..."
pytest tests/unit/ -q

echo ""
echo "================================================================"
echo "  kAI setup complete."
echo ""
echo "  To start the API:"
echo "    source .venv/bin/activate"
echo "    uvicorn kai.elicitation.api:create_app --factory --reload"
echo ""
echo "  Then open frontend/index.html in your browser."
echo "================================================================"
