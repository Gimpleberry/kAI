"""
Enforce Tenet 1: every symbol exported from shared.py must be defined
exactly ONCE across the codebase.

This test scans all Python source under src/kai/ and tests/, looking for
top-level assignments or definitions matching any name in shared.__all__.
The only file allowed to define those names is shared.py itself.

If this test fails, the fix is to delete the duplicate definition and
import from shared instead.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from kai import shared
from kai.shared import REPO_ROOT

# Files allowed to define shared symbols. Just shared.py — that's the point.
ALLOWED_DEFINING_FILES = {
    REPO_ROOT / "src" / "kai" / "shared.py",
}


def _collect_top_level_names(py_file: Path) -> set[str]:
    """Return all top-level names defined in a Python file.

    Includes: module-level assignments, def, async def, class. Does not
    descend into functions or classes — we only care about module-level.
    """
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()

    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
    return names


def _find_python_files() -> list[Path]:
    """Find every .py file we want to scan, skipping the venv and caches."""
    files: list[Path] = []
    for root in [REPO_ROOT / "src", REPO_ROOT / "tests"]:
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            # Skip caches and virtualenvs
            parts = p.parts
            if any(skip in parts for skip in ("__pycache__", ".venv", "venv", ".pytest_cache")):
                continue
            files.append(p)
    return files


def test_shared_symbols_unique() -> None:
    """Each name in shared.__all__ must be defined ONLY in shared.py.

    Defining the same name elsewhere either masks the shared one (a bug
    if the caller meant the shared one) or proves the name should not
    actually be in shared (in which case, remove it).
    """
    shared_names = set(shared.__all__)
    violations: list[str] = []

    for py_file in _find_python_files():
        if py_file in ALLOWED_DEFINING_FILES:
            continue
        defined = _collect_top_level_names(py_file)
        clashes = defined & shared_names
        if clashes:
            for name in sorted(clashes):
                rel = py_file.relative_to(REPO_ROOT)
                violations.append(f"  {rel}: redefines '{name}' (already in shared.__all__)")

    if violations:
        msg = (
            "Tenet 1 violation: shared.py symbols are redefined elsewhere.\n"
            "Fix by importing from kai.shared instead of defining locally.\n\n"
            + "\n".join(violations)
        )
        pytest.fail(msg)


def test_shared_all_matches_definitions() -> None:
    """Every name in shared.__all__ must actually be defined in shared.py."""
    shared_file = REPO_ROOT / "src" / "kai" / "shared.py"
    defined = _collect_top_level_names(shared_file)
    declared = set(shared.__all__)

    missing = declared - defined
    if missing:
        pytest.fail(
            f"shared.__all__ lists names that aren't defined in shared.py: {sorted(missing)}"
        )
