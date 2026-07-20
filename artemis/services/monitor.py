"""
Monitor service — check job liveness + publish status change events.

Used by: worker (cron task), CLI (one-shot debug).
Single source of truth for checking + updating job status.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from artemis.core.config import settings
from artemis.core.database import async_session
from artemis.core.models import Company, Job
from artemis.monitor.checker import CheckResult, JobCheckItem, check_jobs
from artemis.monitor.events import publish_changes

logger = logging.getLogger("artemis.services.monitor")


async def check_active_jobs(
    slug: str | None = None,
    batch_size: int | None = None,
    concurrency: int | None = None,
) -> dict:
    """
    Check a batch of active jobs for liveness.

    Returns: {"checked": int, "ok": int, "inactive": int, "errors": int, "changes": list}
    """
    batch_size = batch_size or settings.monitor_batch_size
    concurrency = concurrency or settings.monitor_concurrency_per_domain
    max_failures = settings.monitor_max_consecutive_failures

    async with async_session() as session:
        q = (
            select(
                Job.id, Job.external_id, Job.url, Job.is_active,
                Job.consecutive_check_failures,
                Company.ats_type, Company.ats_config, Company.slug,
            )
            .join(Company, Job.company_id == Company.id)
            .where(Job.is_active == True)
            .where((Job.check_status.is_(None)) | (Job.check_status != "stale"))
            .order_by(Job.last_checked_at.asc().nulls_first())
            .limit(batch_size)
        )
        if slug:
            q = q.where(Company.slug == slug)
        rows = (await session.execute(q)).all()

    if not rows:
        return {"checked": 0, "ok": 0, "inactive": 0, "errors": 0, "changes": []}

    items = [
        JobCheckItem(
            job_id=str(row.id),
            external_id=row.external_id,
            url=row.url,
            ats_type=row.ats_type.value if row.ats_type else "",
            ats_config=row.ats_config or {},
            company_slug=row.slug,
        )
        for row in rows
    ]

    results = await check_jobs(items, concurrency_per_domain=concurrency)
    failure_counts = {str(row.id): row.consecutive_check_failures or 0 for row in rows}
    now = datetime.now(timezone.utc)

    ok = inactive = errors = 0
    changes = []

    async with async_session() as session:
        for r in results:
            job_id = uuid.UUID(r.job_id)
            job = await session.get(Job, job_id)
            if not job:
                continue

            job.last_checked_at = now

            if r.status == CheckResult.INACTIVE:
                if job.is_active:
                    job.is_active = False
                    job.check_status = "inactive"
                    job.consecutive_check_failures = 0
                    changes.append({
                        "job_id": r.job_id,
                        "url": job.url,
                        "company": next((i.company_slug for i in items if i.job_id == r.job_id), ""),
                        "old_status": "active",
                        "new_status": "inactive",
                        "detail": r.detail,
                        "detected_at": now.isoformat(),
                    })
                inactive += 1

            elif r.status == CheckResult.OK:
                job.check_status = "ok"
                job.consecutive_check_failures = 0
                ok += 1

            elif r.status == CheckResult.ERROR:
                new_failures = failure_counts.get(r.job_id, 0) + 1
                job.consecutive_check_failures = new_failures
                if new_failures >= max_failures:
                    job.check_status = "stale"
                    logger.warning(f"job {r.job_id} marked stale after {new_failures} failures")
                else:
                    job.check_status = "error"
                errors += 1

        await session.commit()

    return {"checked": len(results), "ok": ok, "inactive": inactive, "errors": errors, "changes": changes}


async def run_monitor_cycle() -> dict:
    """Run a single monitor cycle and publish changes to event stream."""
    result = await check_active_jobs()

    if result["changes"]:
        await publish_changes(result["changes"])

    logger.info(f"monitor: {result['checked']} checked, {result['ok']} ok, "
                f"{result['inactive']} inactive, {result['errors']} errors")
    return result
