"""
Taxonomy schema — validated data models for the attribute/level/tenet taxonomy.

Why Pydantic: catches malformed config at startup rather than mid-estimation.
This is the contract every other module relies on — break it here, and
design generation, estimation, and profile output all break in lock step.

Aligned with tenet #5 (QC over backtracking): bad config never reaches the
estimator. The validator below catches:
  - Duplicate IDs within attributes/levels/tenets
  - Tenets referenced by attributes that don't exist
  - Attributes with <2 levels (CBC needs at least binary contrast)
  - Empty taxonomies
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Level(BaseModel):
    """A single discrete value an attribute can take in a CBC bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: Annotated[str, Field(min_length=1, pattern=r"^[a-z0-9_]+$")]
    display: Annotated[str, Field(min_length=1)]
    numeric: float | None = None  # Optional numeric anchor for ordered levels


class Tenet(BaseModel):
    """A high-level engineering principle — aggregated from related attributes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: Annotated[str, Field(min_length=1, pattern=r"^[a-z0-9_]+$")]
    name: Annotated[str, Field(min_length=1)]
    user_definition: Annotated[str, Field(min_length=1)]


class Attribute(BaseModel):
    """An engineering dimension respondents make tradeoffs along."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: Annotated[str, Field(min_length=1, pattern=r"^[a-z0-9_]+$")]
    name: Annotated[str, Field(min_length=1)]
    description: Annotated[str, Field(min_length=1)]
    related_tenets: list[str]
    levels: list[Level]

    @model_validator(mode="after")
    def _validate_levels(self) -> Attribute:
        if len(self.levels) < 2:
            raise ValueError(
                f"Attribute '{self.id}' has <2 levels; CBC requires at least 2 for contrast"
            )
        ids = [lvl.id for lvl in self.levels]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Attribute '{self.id}' has duplicate level ids: {ids}")
        return self


class Taxonomy(BaseModel):
    """Top-level taxonomy: attributes + tenets + cross-references."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str
    attributes: list[Attribute]
    tenets: list[Tenet]

    @model_validator(mode="after")
    def _validate_cross_refs(self) -> Taxonomy:
        if not self.attributes:
            raise ValueError("Taxonomy has no attributes")
        if not self.tenets:
            raise ValueError("Taxonomy has no tenets")

        # Unique IDs at each level
        attr_ids = [a.id for a in self.attributes]
        if len(attr_ids) != len(set(attr_ids)):
            raise ValueError(f"Duplicate attribute ids: {attr_ids}")
        tenet_ids = {t.id for t in self.tenets}
        if len(tenet_ids) != len(self.tenets):
            raise ValueError("Duplicate tenet ids")

        # All related_tenets must reference existing tenets
        for attr in self.attributes:
            unknown = set(attr.related_tenets) - tenet_ids
            if unknown:
                raise ValueError(
                    f"Attribute '{attr.id}' references unknown tenets: {unknown}"
                )

        # Every tenet should be referenced by at least one attribute (else useless)
        referenced = {t for a in self.attributes for t in a.related_tenets}
        orphans = tenet_ids - referenced
        if orphans:
            raise ValueError(
                f"Tenets {orphans} are not referenced by any attribute — "
                f"they will get zero importance in the profile"
            )

        return self

    # Convenience accessors
    def get_attribute(self, attr_id: str) -> Attribute:
        for a in self.attributes:
            if a.id == attr_id:
                return a
        raise KeyError(f"No attribute '{attr_id}'")

    def get_tenet(self, tenet_id: str) -> Tenet:
        for t in self.tenets:
            if t.id == tenet_id:
                return t
        raise KeyError(f"No tenet '{tenet_id}'")

    @property
    def n_estimable_params(self) -> int:
        """Number of part-worth parameters MNL needs to estimate.

        Effects coding: K levels per attribute → K-1 estimable params.
        """
        return sum(len(a.levels) - 1 for a in self.attributes)
