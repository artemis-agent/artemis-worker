import asyncio

import click
from sqlalchemy import select, text


@click.group()
def cli():
    """Artemis - AI-powered job scraping engine"""
    pass


@cli.command("serve-internal")
def serve_internal():
    """Run the internal API server (for Go API to call)."""
    from artemis.internal_api import run_internal_api

    run_internal_api()


@cli.command()
@click.argument("slug")
@click.option("-q", "--query", default="", help="Job title/keyword to search for")
@click.option("-l", "--limit", default=50, help="Max jobs to fetch")
def scrape(slug: str, query: str, limit: int):
    """Scrape jobs for a specific company by slug."""

    async def _run():
        from artemis.core.database import async_session
        from artemis.core.models import Company
        from artemis.services.scrape import scrape_company

        async with async_session() as session:
            result = await session.execute(select(Company).where(Company.slug == slug))
            company = result.scalar_one_or_none()
            if not company:
                click.echo(f"Company '{slug}' not found. Run 'artemis sync-configs' first.")
                return

        click.echo(f"Scraping {company.name} (ATS: {company.ats_type.value})...")
        result = await scrape_company(str(company.id), query=query, limit=limit)
        click.echo(f"  Found {result['jobs_found']} jobs, {result['jobs_new']} new")

    asyncio.run(_run())


@cli.command("scrape-all")
@click.option("-q", "--query", default="", help="Job title/keyword to search for")
@click.option("-l", "--limit", default=50, help="Max jobs per company")
def scrape_all(query: str, limit: int):
    """Scrape jobs for all active companies."""

    async def _run():
        from artemis.services.scrape import scrape_all as _scrape_all

        results = await _scrape_all(query=query, limit=limit)
        total = sum(r.get("jobs_new", 0) for r in results)
        click.echo(f"Scraped {len(results)} companies, {total} new jobs")

    asyncio.run(_run())


@cli.command("init-db")
def init_db():
    """Create all database tables from SQLAlchemy models."""

    async def _init():
        from artemis.core.database import engine
        from artemis.core.models import Base

        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
            for stmt in [
                "CREATE INDEX IF NOT EXISTS ix_jobs_title_fts ON jobs USING gin (to_tsvector('english', title))",
                "CREATE INDEX IF NOT EXISTS ix_jobs_embedding ON jobs USING hnsw (embedding vector_cosine_ops)",
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS last_checked_at TIMESTAMPTZ",
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS check_status VARCHAR(32)",
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS consecutive_check_failures INTEGER DEFAULT 0",
                "CREATE INDEX IF NOT EXISTS ix_jobs_check_schedule ON jobs (last_checked_at ASC NULLS FIRST) WHERE is_active = true",
                # Crunchbase enrichment columns on companies. `website`,
                # `logo_url`, and `description` already exist (shared with
                # the Go API). Only the CB-specific identifiers and the
                # sync timestamp need adding.
                "ALTER TABLE companies ADD COLUMN IF NOT EXISTS crunchbase_permalink VARCHAR(255)",
                "ALTER TABLE companies ADD COLUMN IF NOT EXISTS crunchbase_uuid UUID",
                "ALTER TABLE companies ADD COLUMN IF NOT EXISTS crunchbase_image_id TEXT",
                "ALTER TABLE companies ADD COLUMN IF NOT EXISTS linkedin_url TEXT",
                "ALTER TABLE companies ADD COLUMN IF NOT EXISTS twitter_url TEXT",
                "ALTER TABLE companies ADD COLUMN IF NOT EXISTS facebook_url TEXT",
                "ALTER TABLE companies ADD COLUMN IF NOT EXISTS crunchbase_synced_at TIMESTAMPTZ",
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_companies_crunchbase_permalink ON companies (crunchbase_permalink) WHERE crunchbase_permalink IS NOT NULL",
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_companies_crunchbase_uuid ON companies (crunchbase_uuid) WHERE crunchbase_uuid IS NOT NULL",
            ]:
                await conn.execute(text(stmt))
        click.echo("Database tables and indexes created")

    asyncio.run(_init())


@cli.command("sync-configs")
def sync_configs():
    """Load company YAML configs into the database."""

    async def _sync():
        from artemis.core.config_loader import sync_configs_to_db

        count = await sync_configs_to_db()
        click.echo(f"Synced {count} company configs to database")

    asyncio.run(_sync())


@cli.command("enrich-cb")
@click.option("--slug", default=None, help="Enrich a single company by slug. Omit to backfill many.")
@click.option("--limit", type=int, default=50, help="Max companies to enrich in this run (batch mode).")
@click.option("--force/--no-force", default=False, help="Re-fetch even when crunchbase_synced_at is set.")
@click.option(
    "--sleep",
    "sleep_between",
    type=float,
    default=3.0,
    help="Seconds between calls (default 3s — fits within CB throttle).",
)
def enrich_cb(slug: str | None, limit: int, force: bool, sleep_between: float):
    """Populate Crunchbase fields (website, logo, socials, description)
    on the companies table.

    Examples:
      artemis enrich-cb --slug yubico
      artemis enrich-cb --limit 30
      artemis enrich-cb --slug stripe --force
    """

    async def _run():
        if slug:
            from artemis.services.hunt import enrich_company_from_crunchbase

            result = await enrich_company_from_crunchbase(slug, force=force)
            click.echo(result)
        else:
            from artemis.services.hunt import bulk_enrich_companies_from_crunchbase

            result = await bulk_enrich_companies_from_crunchbase(
                limit=limit,
                force=force,
                sleep_between=sleep_between,
            )
            click.echo(result)

    asyncio.run(_run())


@cli.command()
@click.option("--slug", default=None, help="Company slug to enrich")
def enrich(slug: str | None):
    """Run enrichment workflow (normalize + embed) on unenriched jobs."""

    async def _run():
        from artemis.core.database import async_session
        from artemis.core.models import Job, Company
        from artemis.services.enrich import enrich_jobs

        async with async_session() as session:
            query = select(Job.id).where((Job.normalized_at.is_(None)) | (Job.embedding.is_(None)))
            if slug:
                co = await session.execute(select(Company.id).where(Company.slug == slug))
                company_id = co.scalar_one_or_none()
                if not company_id:
                    click.echo(f"Company '{slug}' not found")
                    return
                query = query.where(Job.company_id == company_id)

            result = await session.execute(query.limit(500))
            job_ids = [str(row[0]) for row in result.all()]

        if not job_ids:
            click.echo("No jobs to enrich")
            return

        click.echo(f"Enriching {len(job_ids)} jobs...")
        stats = await enrich_jobs(job_ids)
        click.echo(f"Done: normalized={stats['normalized']}, embedded={stats['embedded']}")

    asyncio.run(_run())


@cli.command()
def flush():
    """Force-flush the enrichment queue."""

    async def _run():
        from artemis.services.enrich import flush_enrichment_queue

        result = await flush_enrichment_queue()
        if result["drained"] == 0:
            click.echo("Queue empty, nothing to flush")
        else:
            click.echo(
                f"Flushed {result['drained']} jobs: normalized={result['normalized']}, embedded={result['embedded']}"
            )

    asyncio.run(_run())


@cli.command()
@click.argument("careers_url")
def detect(careers_url: str):
    """Detect ATS type for a careers URL."""

    async def _run():
        from artemis.discovery.detector import detect_ats

        result = await detect_ats(careers_url)
        click.echo(f"ATS: {result.ats_type}")
        click.echo(f"Confidence: {result.confidence:.2f}")
        click.echo(f"Config: {result.config}")

    asyncio.run(_run())


@cli.command()
@click.argument("company_name")
@click.option("--url", default=None, help="Careers URL override (auto-searches if omitted)")
def hunt(company_name: str, url: str | None):
    """Hunt a company: find careers page, detect ATS, create config."""

    async def _run():
        from artemis.services.hunt import hunt_company

        click.echo(f"Hunting {company_name}...")
        result = await hunt_company(company_name, careers_url=url)
        status = result.get("status", "unknown")
        if status == "discovered":
            click.echo(f"  ATS: {result['ats_type']} (confidence: {result.get('confidence', 0):.2f})")
            click.echo(f"  URL: {result['careers_url']}")
            click.echo(f"  Jobs found: {result['jobs_found']}")
            click.echo(f"  Config saved to configs/companies/{result['slug']}.yaml")
        elif status == "already_known":
            click.echo(f"  Already known: {result['slug']} ({result['ats_type']})")
        else:
            click.echo(f"  Status: {status}")
            if result.get("detail"):
                click.echo(f"  Detail: {result['detail']}")

    asyncio.run(_run())


@cli.command()
@click.option("--source", default="fortune500", help="Source: fortune500, cloud100, yc, crunchbase")
@click.option("--limit", default=10, help="Max companies to discover")
@click.option("--agent", is_flag=True, help="Run autonomous discovery agent (all sources + AI expansion)")
def discover(source: str, limit: int, agent: bool):
    """Discover and onboard companies from various sources."""

    async def _run():
        if agent:
            from artemis.services.hunt import run_discovery_agent

            click.echo("Running autonomous discovery agent...")
            result = await run_discovery_agent(max_companies=limit)
            click.echo(f"Discovered {result['total_discovered']} companies, {result['total_failed']} failed")
        else:
            from artemis.services.hunt import hunt_from_source

            click.echo(f"Discovering from {source} (limit={limit})...")
            result = await hunt_from_source(source, limit=limit)
            click.echo(f"Discovered {result['discovered']} companies, {result['failed']} failed")

    asyncio.run(_run())


@cli.command()
@click.option("--slug", default=None, help="Only check jobs for this company")
@click.option("-l", "--limit", default=100, help="Max jobs to check")
def monitor(slug: str | None, limit: int):
    """Check active jobs for liveness (one-shot debug)."""

    async def _run():
        from artemis.services.monitor import check_active_jobs

        click.echo(f"Checking jobs{f' for {slug}' if slug else ''}...")
        result = await check_active_jobs(slug=slug, batch_size=limit)

        for change in result["changes"]:
            click.echo(f"  INACTIVE: {change['url']} ({change['detail']})")

        click.echo(f"Done: {result['ok']} ok, {result['inactive']} inactive, {result['errors']} errors")

    asyncio.run(_run())


@cli.command("events")
@click.option("--group", default="cli-debug", help="Consumer group name")
@click.option("--follow", "-f", is_flag=True, help="Continuously consume events")
@click.option("--info", "show_info", is_flag=True, help="Show stream info only")
def events(group: str, follow: bool, show_info: bool):
    """Consume job change events from Redis Stream."""

    async def _run():
        from artemis.monitor.events import consume_events, ack_events, stream_info

        if show_info:
            info = await stream_info()
            click.echo(f"Stream: {info['stream']}")
            click.echo(f"Length: {info['length']}")
            for g in info.get("groups", []):
                click.echo(f"  Group '{g['name']}': {g['pending']} pending, {g['consumers']} consumers")
            return

        click.echo(f"Consuming from group '{group}'...")
        while True:
            batch = await consume_events(group, f"{group}-cli", count=50, block_ms=2000)
            if batch:
                ids = []
                for msg_id, data in batch:
                    click.echo(
                        f"  [{msg_id}] {data.get('new_status', '?'):8s} | {data.get('company', '?')} | {data.get('url', '?')}"
                    )
                    ids.append(msg_id)
                await ack_events(group, ids)
                click.echo(f"  (ack'd {len(ids)} events)")
            if not follow:
                if not batch:
                    click.echo("No pending events")
                break

    asyncio.run(_run())
