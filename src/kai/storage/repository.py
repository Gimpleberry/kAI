"""
Repository layer — encapsulates DB access.

Why repositories: keeps SQL out of business logic, makes testing easy
(swap in in-memory implementations), and centralizes transaction handling.

Tenet #3 alignment: this is the only layer that talks to the DB. If we
ever need to add encryption-at-rest or audit logging, it goes here.
"""

from __future__ import annotations

from kai.storage.models import Session


class SessionRepository:
    """CRUD for Session entities. NOT YET IMPLEMENTED."""

    def __init__(self, db_session: object) -> None:
        self._db = db_session

    def create(self, session: Session) -> Session:
        raise NotImplementedError

    def get(self, session_id: str) -> Session | None:
        raise NotImplementedError

    def update(self, session: Session) -> Session:
        raise NotImplementedError


class ObservationRepository:
    """Bulk inserts for CBC and MaxDiff observations. NOT YET IMPLEMENTED."""

    def __init__(self, db_session: object) -> None:
        self._db = db_session

    def add_cbc(self, session_id: str, observations: list) -> None:
        raise NotImplementedError

    def add_maxdiff(self, session_id: str, observations: list) -> None:
        raise NotImplementedError


class ProfileRepository:
    """Profile persistence with versioning. NOT YET IMPLEMENTED."""

    def __init__(self, db_session: object) -> None:
        self._db = db_session

    def save(self, session_id: str, profile: object) -> int:
        raise NotImplementedError

    def get_latest(self, session_id: str) -> object | None:
        raise NotImplementedError

    def list_all(self, session_id: str) -> list:
        raise NotImplementedError
