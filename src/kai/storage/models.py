"""
SQLAlchemy ORM models — the persistent data layer.

Tables:
    sessions              — one per questionnaire run (resumable)
    cbc_observations      — individual choice responses
    maxdiff_observations  — best/worst responses
    direct_ratings        — anchor ratings
    estimated_profiles    — versioned estimation outputs (full JSON snapshot)

Design choice: using JSON column for `EstimatedProfile` rather than full
relational decomposition. The profile is read-mostly and always consumed
as a unit; relational decomposition would force expensive joins for every
read with no query-pattern benefit.

Design storage policy (ADR-005): we store only the seed and design parameters.
The actual design is regenerated deterministically on demand.

SQLAlchemy 2.0 typed declarative — full mypy support.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class Session(Base):
    """One questionnaire run.

    Design storage policy (ADR-005): we store only the seed and the design
    parameters used. The actual design (specific tasks/alternatives shown)
    is regenerated deterministically on demand via:
        generate_cbc_design(taxonomy, seed=design_seed, **design_params['cbc'])

    This keeps the row small, makes design generation a pure function (easier
    to test), and means design correctness is verifiable against the generator
    rather than trusted from a stored blob.
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    # ADR-005: must match for regeneration to be valid
    taxonomy_version: Mapped[str]
    design_seed: Mapped[int]
    # Snapshot of design_params.yaml at session creation
    design_params: Mapped[dict] = mapped_column(JSON)
    # ADR-005: version the generator alongside taxonomy
    generator_version: Mapped[str]
    # "in_progress" | "completed" | "abandoned"
    status: Mapped[str]

    cbc_observations: Mapped[list[CBCObservation]] = relationship(back_populates="session")
    maxdiff_observations: Mapped[list[MaxDiffObs]] = relationship(back_populates="session")
    direct_ratings: Mapped[list[Rating]] = relationship(back_populates="session")


class CBCObservation(Base):
    __tablename__ = "cbc_observations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    task_id: Mapped[int]
    chosen_alt_index: Mapped[int]
    response_time_ms: Mapped[int]  # for speedrun detection
    created_at: Mapped[datetime]

    session: Mapped[Session] = relationship(back_populates="cbc_observations")


class MaxDiffObs(Base):
    __tablename__ = "maxdiff_observations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    task_id: Mapped[int]
    best_item: Mapped[str]
    worst_item: Mapped[str]
    response_time_ms: Mapped[int]
    created_at: Mapped[datetime]

    session: Mapped[Session] = relationship(back_populates="maxdiff_observations")


class Rating(Base):
    __tablename__ = "direct_ratings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    attribute_id: Mapped[str]
    level_id: Mapped[str]
    rating: Mapped[int]
    created_at: Mapped[datetime]

    session: Mapped[Session] = relationship(back_populates="direct_ratings")


class EstimatedProfileRow(Base):
    """Persisted EstimatedProfile snapshot. Full JSON for read-mostly access."""

    __tablename__ = "estimated_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    estimated_at: Mapped[datetime]
    method: Mapped[str]
    profile_json: Mapped[dict] = mapped_column(JSON)
    quality_gate_passed: Mapped[bool]
