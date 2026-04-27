"""
Session orchestration — the state machine of a questionnaire run.

Phases:
    1. CBC choices       (n_tasks)
    2. MaxDiff tasks     (n_tasks)
    3. Direct ratings    (anchor levels)
    4. Estimation        (server-side)
    5. Profile review    (read-only)

Resume capability: a session in any phase can be picked up where it left off.
The DB is the source of truth; the API is stateless.
"""

from __future__ import annotations


class SessionOrchestrator:
    """Manages questionnaire flow. NOT YET IMPLEMENTED."""

    def create_session(self, taxonomy_path: str) -> str:
        raise NotImplementedError

    def get_next_task(self, session_id: str) -> dict | None:
        raise NotImplementedError

    def record_response(self, session_id: str, response: dict) -> None:
        raise NotImplementedError

    def is_complete(self, session_id: str) -> bool:
        raise NotImplementedError
