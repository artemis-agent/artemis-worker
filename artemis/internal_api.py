"""
Internal HTTP API for the Artemis scraper.

Exposes endpoints that the Go API calls instead of directly
manipulating Redis or Azure OpenAI. This decouples the systems
and keeps all AI/queue logic in Python.

Routes are defined in artemis/api/routes/.
"""

from artemis.api.app import app  # noqa: F401
from artemis.core.config import settings


def run_internal_api():
    """Run the internal API server (called from CLI)."""
    import uvicorn
    port = int(settings.internal_api_port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
