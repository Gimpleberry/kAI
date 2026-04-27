"""
Adaptive question selection — v2 enhancement.

After each response, re-estimate (cheap MNL) and pick the next task that
maximally reduces uncertainty in the part-worths. This means fewer
questions for the same precision, at the cost of design balance.

For v1: not used — fixed design generated up front.
"""

from __future__ import annotations


def select_next_task_adaptive(session_id: str) -> dict:
    """Pick most-informative next task. v2."""
    raise NotImplementedError("Adaptive selection deferred to v2")
