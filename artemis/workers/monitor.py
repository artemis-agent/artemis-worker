"""Monitor worker — Celery task definitions for job liveness checking."""

import asyncio
import logging

from artemis.core.celery_app import app

logger = logging.getLogger("artemis.workers.monitor")


@app.task(name="artemis.workers.monitor.monitor_check_task")
def monitor_check_task():
    """Check active jobs for liveness via ATS APIs."""
    async def _run():
        from artemis.services.monitor import run_monitor_cycle
        await run_monitor_cycle()

    return asyncio.run(_run())
