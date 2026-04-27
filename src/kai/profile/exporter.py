"""
Profile exporters — multiple output formats from a single profile.

Formats:
    - text:     human-readable plain text
    - markdown: structured for docs
    - json:     for programmatic consumers
    - claude_prefs: compact format optimized for Claude settings box
"""

from __future__ import annotations


def export_text(profile_summary: dict) -> str:
    raise NotImplementedError


def export_markdown(profile_summary: dict) -> str:
    raise NotImplementedError


def export_json(profile_summary: dict) -> str:
    raise NotImplementedError


def export_claude_prefs(profile_summary: dict) -> str:
    """Compact format for pasting into Claude settings."""
    raise NotImplementedError
