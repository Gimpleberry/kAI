"""
Tests for the taxonomy schema.

These are the most important tests in the project — the schema is the
contract every other module depends on. If these pass, downstream modules
can rely on the validated objects.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kai.taxonomy.schema import Attribute, Level, Taxonomy, Tenet


def _valid_taxonomy_dict() -> dict:
    """Minimal valid taxonomy used as a starting point in tests."""
    return {
        "version": "1.0",
        "attributes": [
            {
                "id": "test_coverage",
                "name": "Test coverage",
                "description": "Code coverage",
                "related_tenets": ["priority_qc"],
                "levels": [
                    {"id": "low", "display": "60%", "numeric": 60},
                    {"id": "high", "display": "95%", "numeric": 95},
                ],
            }
        ],
        "tenets": [
            {
                "id": "priority_qc",
                "name": "QC-first",
                "user_definition": "Quality over quantity",
            }
        ],
    }


class TestLevel:
    def test_valid_level(self) -> None:
        lvl = Level(id="low", display="60%", numeric=60)
        assert lvl.id == "low"

    def test_id_must_be_lowercase_snake(self) -> None:
        with pytest.raises(ValidationError):
            Level(id="Low", display="60%")
        with pytest.raises(ValidationError):
            Level(id="low-key", display="60%")

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Level(id="low", display="60%", extra_field="boom")  # type: ignore[call-arg]


class TestAttribute:
    def test_valid_attribute(self) -> None:
        attr = Attribute(
            id="test_coverage",
            name="Test coverage",
            description="...",
            related_tenets=["priority_qc"],
            levels=[
                Level(id="low", display="60%"),
                Level(id="high", display="95%"),
            ],
        )
        assert len(attr.levels) == 2

    def test_rejects_single_level(self) -> None:
        with pytest.raises(ValidationError, match="<2 levels"):
            Attribute(
                id="x", name="X", description="x",
                related_tenets=["t"],
                levels=[Level(id="a", display="A")],
            )

    def test_rejects_duplicate_level_ids(self) -> None:
        with pytest.raises(ValidationError, match="duplicate level"):
            Attribute(
                id="x", name="X", description="x",
                related_tenets=["t"],
                levels=[
                    Level(id="a", display="A1"),
                    Level(id="a", display="A2"),
                ],
            )


class TestTaxonomy:
    def test_valid_taxonomy(self) -> None:
        tax = Taxonomy.model_validate(_valid_taxonomy_dict())
        assert len(tax.attributes) == 1
        assert tax.n_estimable_params == 1  # 2 levels - 1

    def test_rejects_unknown_tenet_reference(self) -> None:
        d = _valid_taxonomy_dict()
        d["attributes"][0]["related_tenets"] = ["nonexistent"]
        with pytest.raises(ValidationError, match="unknown tenets"):
            Taxonomy.model_validate(d)

    def test_rejects_orphan_tenet(self) -> None:
        d = _valid_taxonomy_dict()
        d["tenets"].append({
            "id": "orphan", "name": "Orphan",
            "user_definition": "Not used",
        })
        with pytest.raises(ValidationError, match="not referenced"):
            Taxonomy.model_validate(d)

    def test_rejects_duplicate_attribute_ids(self) -> None:
        d = _valid_taxonomy_dict()
        d["attributes"].append(d["attributes"][0])  # duplicate
        with pytest.raises(ValidationError, match="Duplicate attribute"):
            Taxonomy.model_validate(d)

    def test_get_attribute(self) -> None:
        tax = Taxonomy.model_validate(_valid_taxonomy_dict())
        assert tax.get_attribute("test_coverage").id == "test_coverage"
        with pytest.raises(KeyError):
            tax.get_attribute("missing")

    def test_n_estimable_params(self) -> None:
        d = _valid_taxonomy_dict()
        d["attributes"][0]["levels"].append({"id": "med", "display": "80%"})
        tax = Taxonomy.model_validate(d)
        # 3 levels → 2 estimable params (effects coding)
        assert tax.n_estimable_params == 2
