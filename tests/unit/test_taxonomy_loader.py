"""
Tests for the YAML taxonomy loader, including a roundtrip on the real
config/taxonomy.yaml file.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from kai.shared import REPO_ROOT
from kai.taxonomy import load_taxonomy

REAL_TAXONOMY = REPO_ROOT / "config" / "taxonomy.yaml"


def test_real_taxonomy_loads() -> None:
    """The shipped taxonomy.yaml must validate. If this breaks, fix the YAML."""
    if not REAL_TAXONOMY.exists():
        pytest.skip(f"Real taxonomy not present at {REAL_TAXONOMY}")
    tax = load_taxonomy(REAL_TAXONOMY)
    assert tax.version
    assert len(tax.attributes) > 0
    assert len(tax.tenets) > 0


def test_load_from_explicit_path(tmp_path: Path) -> None:
    """Loader honors explicit paths."""
    minimal = {
        "version": "test",
        "attributes": [
            {
                "id": "x",
                "name": "X",
                "description": "X",
                "related_tenets": ["t"],
                "levels": [
                    {"id": "a", "display": "A"},
                    {"id": "b", "display": "B"},
                ],
            }
        ],
        "tenets": [{"id": "t", "name": "T", "user_definition": "T"}],
    }
    p = tmp_path / "tax.yaml"
    p.write_text(yaml.dump(minimal))
    tax = load_taxonomy(p)
    assert tax.version == "test"


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_taxonomy(tmp_path / "nope.yaml")
