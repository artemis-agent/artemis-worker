import pathlib
import re

from artemis.core.config import settings
from artemis.discovery.detector import detect_ats
from artemis.discovery.pr_creator import create_company_pr
from artemis.discovery.sources import get_source_list


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _get_existing_slugs() -> set[str]:
    base = pathlib.Path(settings.configs_dir)
    if not base.exists():
        return set()
    return {p.stem for p in base.glob("*.yaml")}


async def run_discovery(source: str = "fortune500", limit: int = 10) -> dict:
    companies = get_source_list(source)
    existing = _get_existing_slugs()
    results = {"discovered": 0, "already_known": 0, "failed": 0, "prs": []}

    for company in companies[:limit + len(existing)]:
        if results["discovered"] >= limit:
            break

        slug = _slugify(company["name"])
        if slug in existing:
            results["already_known"] += 1
            continue

        careers_url = f"https://{company['careers_hint']}"
        print(f"Discovering {company['name']} ({careers_url})...")

        try:
            detection = await detect_ats(careers_url)

            if detection.ats_type == "unknown" or detection.confidence < 0.5:
                print(f"  Could not detect ATS for {company['name']}: {detection.details}")
                results["failed"] += 1
                continue

            # Test scraping
            sample_jobs = []
            try:
                from artemis.scrapers.registry import get_scraper
                scraper = get_scraper(detection.ats_type, detection.config)
                async with scraper:
                    scraped = await scraper.scrape(query="", limit=5)
                    sample_jobs = [
                        {"title": j.title, "url": j.url, "location": j.location}
                        for j in scraped
                    ]
            except Exception as e:
                print(f"  Test scrape failed: {e}")

            config_data = {
                "name": company["name"],
                "slug": slug,
                "ats": detection.ats_type,
                "careers_url": careers_url,
                "ats_config": detection.config,
                "verified": len(sample_jobs) > 0,
                "last_verified": "2026-04-28" if sample_jobs else None,
            }

            pr_url = await create_company_pr(
                slug=slug,
                config_data=config_data,
                sample_jobs=sample_jobs,
                detection_details=detection.details,
            )

            results["discovered"] += 1
            if pr_url:
                results["prs"].append(pr_url)
            print(f"  Discovered: {company['name']} (ATS: {detection.ats_type}, jobs: {len(sample_jobs)})")

        except Exception as e:
            print(f"  Failed: {company['name']}: {e}")
            results["failed"] += 1

    return results
