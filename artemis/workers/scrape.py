"""Scrape worker — Celery task definitions for job scraping."""

import asyncio
import logging

from artemis.core.celery_app import app

logger = logging.getLogger("artemis.workers.scrape")


@app.task(name="artemis.workers.scrape.scrape_company_task", bind=True, max_retries=2)
def scrape_company_task(self, company_id: str, query: str = "", limit: int = 50):
    """Scrape jobs for a company and enqueue new jobs for enrichment."""
    async def _run():
        from artemis.services.scrape import scrape_company
        from artemis.services.enrich import enqueue_jobs

        result = await scrape_company(company_id, query=query, limit=limit)
        if result["new_job_ids"]:
            depth = await enqueue_jobs(result["new_job_ids"])
            logger.info(f"scraped {result['company_slug']}: {result['jobs_new']} new, enrich queue depth={depth}")
        return {"company": result.get("company_slug"), "new": result.get("jobs_new", 0)}

    return asyncio.run(_run())


@app.task(name="artemis.workers.scrape.scrape_all_task")
def scrape_all_task(query: str = ""):
    """Scrape all active companies."""
    async def _run():
        from artemis.services.scrape import scrape_all
        from artemis.services.enrich import enqueue_jobs

        results = await scrape_all(query=query)
        total_new = 0
        for r in results:
            ids = r.get("new_job_ids", [])
            if ids:
                await enqueue_jobs(ids)
                total_new += len(ids)
        logger.info(f"scrape-all done: {len(results)} companies, {total_new} new jobs enqueued")
        return {"companies": len(results), "new_jobs": total_new}

    return asyncio.run(_run())


@app.task(name="artemis.workers.scrape.hunt_company_task", bind=True, max_retries=1)
def hunt_company_task(self, company_name: str, careers_url: str | None = None):
    """Hunt a company: find careers page, detect ATS, create config."""
    async def _run():
        from artemis.services.hunt import hunt_company
        result = await hunt_company(company_name, careers_url=careers_url)
        logger.info(f"hunt result for {company_name}: {result.get('status')}")
        return result

    return asyncio.run(_run())


@app.task(name="artemis.workers.scrape.discovery_agent_task")
def discovery_agent_task(sources: list[str] | None = None, max_companies: int = 50):
    """Run autonomous discovery agent across sources."""
    async def _run():
        from artemis.services.hunt import run_discovery_agent
        result = await run_discovery_agent(seed_sources=sources, max_companies=max_companies)
        logger.info(f"discovery agent done: {result['total_discovered']} discovered")
        return result

    return asyncio.run(_run())


@app.task(
    name="artemis.workers.scrape.bulk_discover_task",
    time_limit=3600,  # 1 hour cap
    soft_time_limit=3300,
)
def bulk_discover_task(
    sources: str = "fortune500,yc,crunchbase,wellfound",
    limit_per_source: int = 500,
    concurrency: int = 8,
    skip_existing: bool = True,
    skip_test_scrape: bool = False,
):
    """Run bulk company discovery — writes YAMLs directly to disk."""
    import sys

    async def _run():
        # Reuse the script's main() logic by setting argv
        sys.argv = [
            "bulk",
            "--sources", sources,
            "--limit-per-source", str(limit_per_source),
            "--concurrency", str(concurrency),
        ]
        if skip_existing:
            sys.argv.append("--skip-existing")
        if skip_test_scrape:
            sys.argv.append("--skip-test-scrape")

        from artemis.discovery.bulk import main
        await main()

    return asyncio.run(_run())


@app.task(
    name="artemis.workers.scrape.probe_ats_task",
    time_limit=3600,
    soft_time_limit=3300,
)
def probe_ats_task(
    concurrency: int = 20,
    probe_rate: int = 50,
    max_companies: int = 10000,
    skip_existing: bool = True,
    curated_only: bool = False,
):
    """Brute-force probe each ATS API with candidate slugs. Much faster than
    bulk_discover because each probe is a single HTTP call."""
    import sys

    async def _run():
        sys.argv = [
            "probe",
            "--concurrency", str(concurrency),
            "--probe-rate", str(probe_rate),
            "--max", str(max_companies),
        ]
        if skip_existing:
            sys.argv.append("--skip-existing")
        if curated_only:
            sys.argv.append("--curated-only")

        from artemis.discovery.probe import main
        await main()

    return asyncio.run(_run())


@app.task(
    name="artemis.workers.scrape.agent_discover_task",
    time_limit=3600,
    soft_time_limit=3300,
)
def agent_discover_task(
    names: list[str] | None = None,
    concurrency: int = 5,
    max_companies: int = 5000,
    dry_run: bool = False,
):
    """AI-powered company discovery: search-grounded ATS detection.
    If `names` is None, picks the next `max_companies` unprocessed entries
    from the curated + Fortune-500 lists."""
    async def _run():
        from artemis.discovery.bulk import (
            bulk_discover_via_agent,
            _candidates_not_yet_known,
        )
        targets = names or _candidates_not_yet_known(max_companies)
        result = await bulk_discover_via_agent(
            targets,
            concurrency=concurrency,
            max_companies=max_companies,
            dry_run=dry_run,
        )
        logger.info(
            f"agent_discover_task done: {result['hits']}/{result['total']} hits, "
            f"cost ~${result['est_cost_usd']}"
        )
        return result

    return asyncio.run(_run())


@app.task(name="artemis.workers.scrape.daily_agent_discover_task")
def daily_agent_discover_task(daily_cap: int = 30):
    """Scheduled daily task: discover up to `daily_cap` new companies via the
    AI agent. Source: next unprocessed curated/F500 names."""
    async def _run():
        from artemis.discovery.bulk import (
            bulk_discover_via_agent,
            _candidates_not_yet_known,
        )
        targets = _candidates_not_yet_known(daily_cap)
        if not targets:
            logger.info("daily agent discover: no candidates left to process")
            return {"total": 0, "hits": 0}
        result = await bulk_discover_via_agent(
            targets,
            concurrency=5,
            max_companies=daily_cap,
            summary_path=f"/tmp/agent_discover_daily.json",
        )
        logger.info(
            f"daily agent discover: {result['hits']}/{result['total']} new companies "
            f"(cost ~${result['est_cost_usd']})"
        )
        return result

    return asyncio.run(_run())
