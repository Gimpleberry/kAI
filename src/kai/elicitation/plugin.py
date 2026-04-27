"""
Elicitation plugin — FastAPI server, loaded last because it serves
everything else.

Per Tenet 2 (efficient): heavy startup checks (DB warmup, taxonomy validation,
etc.) are owned by earlier plugins, so by the time this plugin starts, the
HTTP server can bind and become reachable immediately.

Owns:
  - FastAPI app instance
  - uvicorn server lifecycle (when run via main.py)

Depends on:
  - All earlier plugins being started

Note: For development with --reload, run uvicorn directly against
kai.elicitation.api:create_app instead of going through main.py.
"""

from __future__ import annotations

import logging
from typing import Any

from kai.shared import get_config_value

logger = logging.getLogger("kai.elicitation.plugin")


class ElicitationPlugin:
    """Lifecycle wrapper for the FastAPI elicitation server."""

    def __init__(self) -> None:
        self._server: Any = None

    def start(self) -> None:
        host = get_config_value("HOST", default="127.0.0.1")
        port = int(get_config_value("PORT", default="8000"))
        logger.info("Elicitation API binding to %s:%d", host, port)
        # TODO: instantiate FastAPI app via create_app(), start uvicorn
        # in a background thread or task.

    def stop(self) -> None:
        if self._server is not None:
            try:
                self._server.shutdown()  # placeholder API
            except Exception:
                logger.exception("Error stopping elicitation server")
            self._server = None
