#!/usr/bin/env bash
# Installs git hooks from scripts/ into .git/hooks/
# Run once after cloning the repo.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -d .git ]]; then
    echo "ERROR: not a git repository. Run 'git init' first." >&2
    exit 1
fi

cp scripts/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

echo "✓ pre-commit hook installed at .git/hooks/pre-commit"
echo "  Blocks commits of .db files, .env, data/, etc."
echo "  See DECISIONS.md → ADR-003"
