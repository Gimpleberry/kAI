"""
FastAPI elicitation API.

Endpoints:
    POST /sessions                    Create new questionnaire session
    GET  /sessions/{id}               Resume existing session
    GET  /sessions/{id}/next-task     Fetch the next question
    POST /sessions/{id}/responses     Submit a response
    POST /sessions/{id}/estimate      Trigger estimation (returns profile)
    GET  /sessions/{id}/profile       Latest estimated profile
    GET  /sessions/{id}/diagnostics   Quality reports

Frontend hits these from the browser. Stateless except for the DB —
all session state lives in storage so we can resume across restarts.

NOT YET IMPLEMENTED — scaffolding stub.
"""

from __future__ import annotations

# from fastapi import FastAPI


def create_app() -> object:
    """FastAPI app factory. NOT YET IMPLEMENTED."""
    raise NotImplementedError("API endpoints pending — scaffolding only")
