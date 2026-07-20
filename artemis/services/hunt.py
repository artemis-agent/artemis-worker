"""
Hunt service — find a company's careers page, detect ATS, create config, scrape.

Two modes:
1. User-triggered: "find jobs at {company_name}" → search → detect → config → scrape
2. Autonomous agent: BFS through sources, AI-powered similar company expansion
"""

import logging
import pathlib
import re
from datetime import datetime, timezone

import yaml
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from artemis.core.config import settings
from artemis.core.database import async_session
from artemis.core.models import Company, CompanyStatus

logger = logging.getLogger("artemis.services.hunt")


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


# ── User-triggered hunt ──────────────────────────────────────────────────


async def hunt_company(company_name: str, careers_url: str | None = None) -> dict:
    """
    Hunt a single company: find careers page → detect ATS → create config → optionally scrape.

    Args:
        company_name: Company name (e.g., "Stripe")
        careers_url: Optional careers URL override. If None, searches via DDG.

    Returns: {"slug", "name", "ats_type", "careers_url", "config", "status", "jobs_found"}
    """
    slug = _slugify(company_name)

    # Check if we already know this company.
    async with async_session() as session:
        result = await session.execute(select(Company).where(Company.slug == slug))
        existing = result.scalar_one_or_none()
        if existing:
            return {
                "slug": slug,
                "name": existing.name,
                "ats_type": existing.ats_type.value,
                "careers_url": existing.careers_url,
                "status": "already_known",
                "jobs_found": 0,
            }

    # Run the AI-powered discovery agent (search → regex → probe → verify).
    from artemis.discovery.agent import discover_company

    discovery = await discover_company(company_name, website=careers_url)

    if discovery.status != "discovered" or not discovery.ats:
        return {
            "slug": slug,
            "name": company_name,
            "careers_url": discovery.careers_url or careers_url,
            "status": discovery.status,
            "detail": discovery.error,
        }

    # Persist to DB (the agent already wrote the YAML).
    async with async_session() as session:
        stmt = (
            pg_insert(Company)
            .values(
                name=company_name,
                slug=slug,
                ats_type=discovery.ats,
                careers_url=discovery.careers_url or "",
                ats_config=discovery.ats_config or {},
                status=CompanyStatus.active,
            )
            .on_conflict_do_update(
                index_elements=["slug"],
                set_={
                    "ats_type": discovery.ats,
                    "careers_url": discovery.careers_url or "",
                    "ats_config": discovery.ats_config or {},
                },
            )
        )
        await session.execute(stmt)
        await session.commit()

    logger.info(
        f"hunted {company_name}: ats={discovery.ats}, jobs={discovery.discovered_jobs}, "
        f"calls=search:{discovery.search_calls}+llm:{discovery.llm_calls}"
    )

    return {
        "slug": slug,
        "name": company_name,
        "ats_type": discovery.ats,
        "careers_url": discovery.careers_url or "",
        "config": discovery.ats_config or {},
        "status": "discovered",
        "jobs_found": discovery.discovered_jobs,
        "evidence_url": discovery.evidence_url,
        "llm_calls": discovery.llm_calls,
    }


# ── Batch hunt (from dynamic sources) ────────────────────────────────────


async def hunt_from_source(source: str, limit: int = 50) -> dict:
    """Hunt companies from a source (crunchbase, yc, fortune500, cloud100)."""
    from artemis.discovery.sources import get_source_list, get_dynamic_source

    # Try static first, then dynamic
    companies = get_source_list(source)
    if not companies:
        companies = await get_dynamic_source(source, limit=limit * 2)

    if not companies:
        return {"source": source, "total": 0, "discovered": 0, "failed": 0}

    # Get existing slugs to skip
    async with async_session() as session:
        result = await session.execute(select(Company.slug))
        existing_slugs = {row.slug for row in result.all()}

    discovered = 0
    failed = 0

    for co in companies:
        if discovered >= limit:
            break

        name = co.get("name", "")
        slug = _slugify(name)
        if slug in existing_slugs or not name:
            continue

        # For static lists, use careers_hint directly
        careers_url = None
        if co.get("careers_hint"):
            careers_url = f"https://{co['careers_hint']}"
        elif co.get("website"):
            # Try website + /careers
            website = co["website"].rstrip("/")
            if not website.startswith("http"):
                website = f"https://{website}"
            careers_url = f"{website}/careers"

        try:
            result = await hunt_company(name, careers_url=careers_url)
            if result.get("status") == "discovered":
                discovered += 1
                existing_slugs.add(slug)
            elif result.get("status") == "already_known":
                pass
            else:
                failed += 1
        except Exception as e:
            logger.error(f"hunt failed for {name}: {e}")
            failed += 1

    return {"source": source, "total": len(companies), "discovered": discovered, "failed": failed}


# ── Crunchbase enrichment ────────────────────────────────────────────────


async def enrich_company_from_crunchbase(
    slug: str,
    *,
    force: bool = False,
) -> dict:
    """Populate the Crunchbase columns on a single `Company` row.

    Lookup order for the CB permalink:
      1. The row's existing `crunchbase_permalink` (if previously set)
      2. The company's `slug` (works when the slug == CB permalink, which
         is the case for everything `discover_company` writes)

    Pass `force=True` to re-fetch even if `crunchbase_synced_at` is set;
    otherwise an already-enriched row is skipped.

    Returns one of: `enriched`, `already_synced`, `not_found`,
    `unknown_slug`, `error`.
    """
    from artemis.discovery.sources import fetch_crunchbase_profile

    async with async_session() as session:
        row = (await session.execute(select(Company).where(Company.slug == slug))).scalar_one_or_none()
        if row is None:
            return {"slug": slug, "status": "unknown_slug"}

        if row.crunchbase_synced_at is not None and not force:
            return {
                "slug": slug,
                "status": "already_synced",
                "synced_at": row.crunchbase_synced_at.isoformat(),
            }

        permalink = row.crunchbase_permalink or row.slug
        try:
            profile = await fetch_crunchbase_profile(permalink)
        except Exception as e:
            logger.exception(f"crunchbase enrich error for {slug}")
            return {"slug": slug, "status": "error", "error": str(e)}

        if profile is None:
            # Cache the miss so we don't re-hammer the CB API for orgs
            # that don't exist there.
            row.crunchbase_synced_at = datetime.now(timezone.utc)
            await session.commit()
            return {"slug": slug, "status": "not_found", "permalink": permalink}

        # Apply only the CB-managed fields — don't clobber `name`,
        # `slug`, `careers_url`, `ats_config`, etc.
        for col in (
            "crunchbase_permalink",
            "crunchbase_uuid",
            "crunchbase_image_id",
            "website",
            "logo_url",
            "description",
            "linkedin_url",
            "twitter_url",
            "facebook_url",
        ):
            val = profile.get(col)
            if val is not None:
                setattr(row, col, val)
        row.crunchbase_synced_at = datetime.now(timezone.utc)
        await session.commit()
        return {
            "slug": slug,
            "status": "enriched",
            "permalink": profile.get("crunchbase_permalink"),
            "website": profile.get("website"),
            "logo_url": profile.get("logo_url"),
        }


async def bulk_enrich_companies_from_crunchbase(
    *,
    limit: int = 50,
    force: bool = False,
    sleep_between: float = 3.0,
) -> dict:
    """Enrich up to `limit` companies missing Crunchbase data.

    Picks rows where `crunchbase_synced_at IS NULL` (or all rows when
    `force=True`), oldest-updated first. Spaces calls by `sleep_between`
    seconds to stay under the Crunchbase per-minute throttle (our tier
    starts 429'ing after ~8 calls/minute).

    Stops early if Crunchbase begins returning errors (signalled by an
    `error` status from `enrich_company_from_crunchbase`).
    """
    import asyncio

    async with async_session() as session:
        q = select(Company.slug).order_by(Company.updated_at.asc()).limit(limit)
        if not force:
            q = q.where(Company.crunchbase_synced_at.is_(None))
        slugs = [r[0] for r in (await session.execute(q)).all()]

    counts = {"enriched": 0, "not_found": 0, "already_synced": 0, "error": 0, "unknown_slug": 0}
    processed: list[dict] = []
    for i, slug in enumerate(slugs):
        if i > 0:
            await asyncio.sleep(sleep_between)
        r = await enrich_company_from_crunchbase(slug, force=force)
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        processed.append(r)
        logger.info(f"cb-enrich {i + 1}/{len(slugs)} {slug}: {r['status']}")
        if r["status"] == "error":
            logger.warning("cb-enrich: stopping early after error")
            break
    return {"requested": len(slugs), "processed": len(processed), **counts}


# ── Autonomous discovery agent (BFS + AI expansion) ──────────────────────


async def run_discovery_agent(seed_sources: list[str] | None = None, max_companies: int = 100) -> dict:
    """
    Autonomous BFS agent that discovers companies from multiple sources
    and expands using AI-powered similar company search.

    Process:
    1. Gather seed companies from all sources (Crunchbase, YC, Fortune, Cloud100)
    2. For each discovered company, search for similar companies (DDG)
    3. BFS expansion: queue neighbors, check each
    4. Stop when max_companies reached or no more leads
    """
    if seed_sources is None:
        seed_sources = ["fortune500", "cloud100", "yc", "wellfound", "builtin"]
        if settings.crunchbase_api_key:
            seed_sources.append("crunchbase")

    total_discovered = 0
    total_failed = 0
    sources_processed = []

    for source in seed_sources:
        remaining = max_companies - total_discovered
        if remaining <= 0:
            break

        result = await hunt_from_source(source, limit=remaining)
        total_discovered += result["discovered"]
        total_failed += result["failed"]
        sources_processed.append(result)
        logger.info(f"agent: source={source}, discovered={result['discovered']}")

    # Phase 2: AI-powered expansion via DDG similar company search
    if total_discovered < max_companies:
        expansion = await _expand_via_search(max_companies - total_discovered)
        total_discovered += expansion["discovered"]
        total_failed += expansion["failed"]

    return {
        "total_discovered": total_discovered,
        "total_failed": total_failed,
        "sources": sources_processed,
    }


async def _expand_via_search(limit: int) -> dict:
    """Discover more companies by searching for 'top tech companies hiring' etc."""

    search_queries = [
        "top tech startups hiring 2026",
        "best AI companies careers",
        "fast growing SaaS companies jobs",
        "YC startup careers page",
        "Series B startup hiring engineers",
    ]

    discovered = 0
    failed = 0

    for query in search_queries:
        if discovered >= limit:
            break

        try:
            import httpx
            from bs4 import BeautifulSoup

            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                for link in soup.select("a.result__a")[:10]:
                    title = link.get_text().strip()
                    # Extract company name from search result titles
                    # Simple heuristic: take the first part before " - " or " | "
                    name = re.split(r"\s*[-|–—]\s*", title)[0].strip()
                    if len(name) > 3 and len(name) < 50:
                        try:
                            result = await hunt_company(name)
                            if result.get("status") == "discovered":
                                discovered += 1
                            else:
                                failed += 1
                        except Exception:
                            failed += 1

                    if discovered >= limit:
                        break
        except Exception as e:
            logger.debug(f"expansion search failed for '{query}': {e}")

    return {"discovered": discovered, "failed": failed}


# ── Config file management ────────────────────────────────────────────────


def _save_config(slug: str, config_data: dict):
    """Save company config as YAML file."""
    configs_dir = pathlib.Path(settings.configs_dir)
    configs_dir.mkdir(parents=True, exist_ok=True)

    filepath = configs_dir / f"{slug}.yaml"
    with open(filepath, "w") as f:
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
    logger.info(f"saved config: {filepath}")
