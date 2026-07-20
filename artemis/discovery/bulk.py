"""Bulk company discovery — runs detection on hundreds of companies and writes
config YAMLs directly to disk (no GitHub PR).

Usage:
    docker exec artemis-worker-scrape-worker-1 python3 -m artemis.discovery.bulk \\
        --sources fortune500,yc,crunchbase \\
        --limit-per-source 500 \\
        --concurrency 5 \\
        --skip-existing

Outputs:
    configs/companies/*.yaml  — one per successfully detected company
    /tmp/bulk_discovery_summary.json  — full results log
"""

import argparse
import asyncio
import json
import logging
import pathlib
import re
import time
from urllib.parse import urlparse

import yaml

from artemis.core.config import settings
from artemis.discovery.detector import detect_ats
from artemis.discovery.sources import (
    FORTUNE_500_COMPANIES,
    fetch_crunchbase_top,
    fetch_yc_companies,
    fetch_wellfound_companies,
)

logger = logging.getLogger("artemis.discovery.bulk")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def existing_slugs() -> set[str]:
    base = pathlib.Path(settings.configs_dir)
    if not base.exists():
        return set()
    return {p.stem for p in base.glob("*.yaml")}


def website_to_careers_hint(website: str | None) -> str | None:
    if not website:
        return None
    parsed = urlparse(website if website.startswith("http") else f"https://{website}")
    host = parsed.netloc or parsed.path
    if not host:
        return None
    # Try common patterns: careers.{domain}, {domain}/careers, jobs.{domain}
    return f"{host}/careers"


async def gather_sources(use_sources: set[str], limit_per: int) -> list[dict]:
    """Pull companies from all requested sources, dedupe by slug."""
    all_companies: list[dict] = []

    if "fortune500" in use_sources:
        for c in FORTUNE_500_COMPANIES:
            all_companies.append(
                {
                    "name": c["name"],
                    "careers_url": f"https://{c['careers_hint']}",
                    "source": "fortune500",
                }
            )
        logger.info(f"loaded {len(FORTUNE_500_COMPANIES)} from fortune500")

    if "yc" in use_sources:
        try:
            yc = await fetch_yc_companies(limit=limit_per)
            for c in yc:
                hint = website_to_careers_hint(c.get("website"))
                if hint:
                    all_companies.append(
                        {
                            "name": c["name"],
                            "careers_url": f"https://{hint}",
                            "source": "yc",
                        }
                    )
            logger.info(f"loaded {len(yc)} from yc")
        except Exception as e:
            logger.error(f"YC source failed: {e}")

    if "crunchbase" in use_sources:
        try:
            cb = await fetch_crunchbase_top(limit=limit_per)
            for c in cb:
                hint = website_to_careers_hint(c.get("website"))
                if hint:
                    all_companies.append(
                        {
                            "name": c["name"],
                            "careers_url": f"https://{hint}",
                            "source": "crunchbase",
                        }
                    )
            logger.info(f"loaded {len(cb)} from crunchbase")
        except Exception as e:
            logger.error(f"Crunchbase source failed: {e}")

    if "wellfound" in use_sources:
        try:
            wf = await fetch_wellfound_companies(limit=limit_per)
            for c in wf:
                hint = website_to_careers_hint(c.get("website"))
                if hint:
                    all_companies.append(
                        {
                            "name": c["name"],
                            "careers_url": f"https://{hint}",
                            "source": "wellfound",
                        }
                    )
            logger.info(f"loaded {len(wf)} from wellfound")
        except Exception as e:
            logger.error(f"Wellfound source failed: {e}")

    # Dedupe by slug
    seen: dict[str, dict] = {}
    for c in all_companies:
        slug = slugify(c["name"])
        if slug and slug not in seen:
            c["slug"] = slug
            seen[slug] = c
    deduped = list(seen.values())
    logger.info(f"After dedupe: {len(deduped)} unique companies")
    return deduped


async def discover_one(
    company: dict,
    sem: asyncio.Semaphore,
    configs_dir: pathlib.Path,
    skip_test_scrape: bool,
) -> dict:
    """Detect ATS + optionally test-scrape + write YAML. Returns result dict."""
    async with sem:
        result = {
            "slug": company["slug"],
            "name": company["name"],
            "source": company["source"],
            "careers_url": company["careers_url"],
            "status": "unknown",
            "ats": None,
            "details": None,
            "confidence": 0.0,
            "test_jobs": 0,
        }
        start = time.time()
        try:
            # Hard 45s cap per company so a single slow site can't hang the whole batch
            detection = await asyncio.wait_for(
                detect_ats(company["careers_url"]),
                timeout=45,
            )
            result["ats"] = detection.ats_type
            result["details"] = detection.details
            result["confidence"] = detection.confidence

            if detection.ats_type == "unknown" or detection.confidence < 0.5:
                result["status"] = "no_ats_detected"
                result["elapsed"] = round(time.time() - start, 1)
                return result

            # Optional: test scrape (just 1-2 jobs to validate)
            sample_count = 0
            if not skip_test_scrape:
                try:
                    from artemis.scrapers.registry import get_scraper

                    scraper = get_scraper(detection.ats_type, detection.config)
                    async with scraper:
                        scraped = await asyncio.wait_for(
                            scraper.scrape(query="", limit=2),
                            timeout=20,
                        )
                        sample_count = len(scraped)
                except Exception as e:
                    logger.debug(f"{company['slug']}: test-scrape failed: {e}")
                    result["status"] = "scrape_failed"
                    result["test_error"] = str(e)[:200]
                    result["elapsed"] = round(time.time() - start, 1)
                    return result

            result["test_jobs"] = sample_count

            # Write the YAML
            config_data = {
                "name": company["name"],
                "slug": company["slug"],
                "ats": detection.ats_type,
                "careers_url": company["careers_url"],
                "ats_config": detection.config,
                "verified": sample_count > 0,
                "discovered_from": company["source"],
            }
            path = configs_dir / f"{company['slug']}.yaml"
            with open(path, "w") as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

            result["status"] = "ok" if sample_count > 0 else "ok_unverified"
            result["yaml_path"] = str(path)
        except asyncio.TimeoutError:
            result["status"] = "timeout"
            result["error"] = "detection exceeded 45s"
        except Exception as e:
            result["status"] = "error"
            result["error"] = f"{type(e).__name__}: {e}"
        result["elapsed"] = round(time.time() - start, 1)
        return result


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sources", default="fortune500,yc,crunchbase,wellfound", help="comma-separated list of sources"
    )
    parser.add_argument("--limit-per-source", type=int, default=500, help="max companies pulled per dynamic source")
    parser.add_argument("--concurrency", type=int, default=5, help="parallel detections (each makes 3-5 HTTP calls)")
    parser.add_argument(
        "--skip-existing", action="store_true", default=True, help="skip slugs that already have a YAML"
    )
    parser.add_argument(
        "--skip-test-scrape", action="store_true", help="skip the test-scrape step (faster, less reliable)"
    )
    parser.add_argument("--summary-path", default="/tmp/bulk_discovery_summary.json")
    parser.add_argument("--max", type=int, default=10000, help="hard cap on total companies to process")
    args = parser.parse_args()

    use_sources = set(s.strip() for s in args.sources.split(",") if s.strip())
    companies = await gather_sources(use_sources, args.limit_per_source)
    companies = companies[: args.max]

    configs_dir = pathlib.Path(settings.configs_dir)
    configs_dir.mkdir(parents=True, exist_ok=True)

    if args.skip_existing:
        existing = existing_slugs()
        before = len(companies)
        companies = [c for c in companies if c["slug"] not in existing]
        logger.info(f"Skipping {before - len(companies)} already-known slugs, processing {len(companies)}")

    if not companies:
        logger.info("Nothing to do.")
        return

    sem = asyncio.Semaphore(args.concurrency)
    results: list[dict] = []
    started = time.time()

    async def wrapped(c):
        r = await discover_one(c, sem, configs_dir, args.skip_test_scrape)
        results.append(r)
        # Progress every 20
        n = len(results)
        if n % 20 == 0 or n == len(companies):
            ok = sum(1 for x in results if x["status"] in ("ok", "ok_unverified"))
            elapsed = time.time() - started
            rate = n / elapsed if elapsed > 0 else 0
            logger.info(
                f"  Progress: {n}/{len(companies)} "
                f"({ok} ok, {n - ok} failed)  "
                f"rate={rate:.1f}/s  elapsed={elapsed:.0f}s"
            )
        return r

    await asyncio.gather(*(wrapped(c) for c in companies))

    # Summary
    by_status: dict[str, int] = {}
    by_ats: dict[str, int] = {}
    by_source: dict[str, dict] = {}
    for r in results:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        if r["ats"]:
            by_ats[r["ats"]] = by_ats.get(r["ats"], 0) + 1
        src = r["source"]
        if src not in by_source:
            by_source[src] = {"total": 0, "ok": 0}
        by_source[src]["total"] += 1
        if r["status"] in ("ok", "ok_unverified"):
            by_source[src]["ok"] += 1

    print(f"\n{'═' * 70}")
    print(f"  BULK DISCOVERY RESULTS — {len(results)} companies, {time.time() - started:.0f}s")
    print(f"{'═' * 70}")
    print("\nBy status:")
    for s, n in sorted(by_status.items(), key=lambda x: -x[1]):
        print(f"  {s:<20} {n}")
    print("\nBy detected ATS:")
    for ats, n in sorted(by_ats.items(), key=lambda x: -x[1]):
        print(f"  {ats:<20} {n}")
    print("\nBy source:")
    for s, d in by_source.items():
        pct = 100 * d["ok"] / d["total"] if d["total"] else 0
        print(f"  {s:<15} {d['ok']:>4}/{d['total']:<4} ({pct:.0f}% success)")

    with open(args.summary_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nFull results written to: {args.summary_path}")


# ── AI-powered agent variant (search-grounded discovery) ─────────────────


async def bulk_discover_via_agent(
    names: list[str],
    *,
    concurrency: int = 5,
    max_companies: int | None = None,
    summary_path: str = "/tmp/agent_discover_summary.json",
    dry_run: bool = False,
) -> dict:
    """Run `discover_company` over a list of company names with bounded
    concurrency. Designed to drive the daily-cap incremental task and the
    one-off initial bulk run.

    Returns aggregate stats and writes a per-company summary JSON.
    """
    import httpx
    from artemis.discovery.agent import (
        DiscoveryResult,
        discover_company,
        UA,
    )
    from artemis.discovery.search import default_searcher

    if max_companies is not None:
        names = names[:max_companies]

    sem = asyncio.Semaphore(concurrency)
    searcher = default_searcher()
    started = time.time()
    results: list[DiscoveryResult] = []
    done = 0

    async with httpx.AsyncClient(
        headers={"User-Agent": UA},
        follow_redirects=True,
        timeout=15.0,
    ) as client:

        async def _one(name: str):
            nonlocal done
            async with sem:
                r = await discover_company(
                    name,
                    searcher=searcher,
                    http_client=client,
                    dry_run=dry_run,
                )
                done += 1
                if done % 10 == 0:
                    elapsed = time.time() - started
                    rate = done / elapsed if elapsed > 0 else 0
                    hits = sum(1 for x in results if x.status == "discovered")
                    logger.info(f"agent-bulk: {done}/{len(names)} ({hits} hits) rate={rate:.1f}/s")
                return r

        results = await asyncio.gather(*(_one(n) for n in names))

    elapsed = time.time() - started
    hits = [r for r in results if r.status == "discovered"]
    summary = {
        "total": len(names),
        "hits": len(hits),
        "not_found": sum(1 for r in results if r.status == "not_found"),
        "already_known": sum(1 for r in results if r.status == "already_known"),
        "errors": sum(1 for r in results if r.status == "error"),
        "elapsed_sec": round(elapsed, 1),
        "total_llm_calls": sum(r.llm_calls for r in results),
        "total_search_calls": sum(r.search_calls for r in results),
        "est_cost_usd": round(sum(r.llm_calls for r in results) * 0.01, 4),
        "by_ats": {},
        "results": [
            {
                "name": r.name,
                "slug": r.slug,
                "status": r.status,
                "ats": r.ats,
                "jobs": r.discovered_jobs,
                "evidence_url": r.evidence_url,
                "llm_calls": r.llm_calls,
                "elapsed_sec": round(r.elapsed_sec, 2),
            }
            for r in results
        ],
    }
    for r in hits:
        summary["by_ats"][r.ats] = summary["by_ats"].get(r.ats, 0) + 1

    try:
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        logger.info(f"agent-bulk summary written to {summary_path}")
    except Exception as e:
        logger.warning(f"agent-bulk: failed to write summary: {e}")

    logger.info(
        f"agent-bulk COMPLETE: {len(hits)}/{len(names)} hits in {elapsed:.0f}s (cost ~${summary['est_cost_usd']})"
    )
    return summary


def _candidates_not_yet_known(limit: int) -> list[str]:
    """Pick the next `limit` names from curated + Fortune 500 lists whose
    slug is not yet present in `configs/companies/`. Used by the daily task."""
    from artemis.discovery.curated import fetch_curated

    existing = {p.stem for p in pathlib.Path(settings.configs_dir).glob("*.yaml")}
    pool: list[str] = []
    for entry in fetch_curated():
        pool.append(entry["name"])
    for entry in FORTUNE_500_COMPANIES:
        pool.append(entry["name"])

    def _slugify(name: str) -> str:
        s = name.lower().strip()
        s = re.sub(r"[^a-z0-9]+", "-", s)
        return s.strip("-")

    out: list[str] = []
    seen: set[str] = set()
    for name in pool:
        slug = _slugify(name)
        if slug in existing or slug in seen:
            continue
        seen.add(slug)
        out.append(name)
        if len(out) >= limit:
            break
    return out


if __name__ == "__main__":
    asyncio.run(main())
