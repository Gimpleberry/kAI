"""
Taxonomy YAML loader — reads config/taxonomy.yaml and validates it against the schema.

Centralizes config loading so every other module gets a validated Taxonomy
object rather than parsing YAML themselves. Path is configurable for testing.

Path resolution comes from kai.shared (per Tenet 1: shared owns paths).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from kai.shared import TAXONOMY_PATH
from kai.taxonomy.schema import Taxonomy


def load_taxonomy(path: Path | str | None = None) -> Taxonomy:
    """Load and validate the taxonomy from a YAML file.

    Args:
        path: Path to taxonomy YAML. Defaults to TAXONOMY_PATH from shared.py.

    Returns:
        Validated Taxonomy object.

    Raises:
        FileNotFoundError: If path doesn't exist.
        pydantic.ValidationError: If YAML doesn't conform to schema.
    """
    target = Path(path) if path else TAXONOMY_PATH
    if not target.exists():
        raise FileNotFoundError(f"Taxonomy file not found: {target}")

    with target.open() as f:
        raw = yaml.safe_load(f)

    return Taxonomy.model_validate(raw)
