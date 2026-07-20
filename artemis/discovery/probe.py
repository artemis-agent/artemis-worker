"""Brute-force ATS probing — much faster than detect_ats() because we skip
the multi-strategy detection and directly hit each ATS's job-board API with
candidate slugs.

For each candidate company slug, we send one HTTP request per ATS:
  - Greenhouse:      GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
  - Lever:           GET https://api.lever.co/v0/postings/{slug}?mode=json&limit=1
  - Ashby:           GET https://api.ashbyhq.com/posting-api/job-board/{slug}
  - SmartRecruiters: GET https://api.smartrecruiters.com/v1/companies/{slug}/postings
  - Eightfold:       GET https://{slug}.eightfold.ai/api/pcsx/search?domain={slug}.com

We accept the FIRST ATS that returns a non-empty job list. Writes a YAML config
for each successful hit, then syncs to the DB.

Usage:
    docker exec artemis-worker-scrape-worker-1 python3 -m artemis.discovery.probe
"""

import argparse
import asyncio
import json
import logging
import pathlib
import re
import time

import httpx
import yaml

from artemis.core.config import settings
from artemis.discovery.curated import fetch_curated
from artemis.discovery.sources import (
    FORTUNE_500_COMPANIES,
    fetch_crunchbase_top,
    fetch_yc_companies,
    fetch_wellfound_companies,
)

logger = logging.getLogger("artemis.discovery.probe")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


_COMMON_FIRST_WORDS = {
    # Generic English words / numbers / pronouns — never useful as ATS slugs
    # alone, used to filter SHORT first-word variants from multi-word names
    # (e.g. "Eli Lilly" → "eli" must not match a random Ashby "eli" board).
    "the", "a", "an", "us", "uk", "new", "old", "big", "all", "any", "one",
    "two", "three", "four", "five", "first", "last", "next", "best", "top",
    "good", "great", "smart", "global", "national", "international", "general",
    "united", "american", "world", "open", "free", "true", "blue", "red",
    "green", "black", "white", "gold", "silver", "core", "main", "prime",
    "alpha", "beta", "delta", "north", "south", "east", "west", "central",
    "capital", "industries", "industry", "group", "company", "co", "corp",
    "labs", "lab", "studio", "studios", "media", "systems", "system",
    "solutions", "services", "consulting", "partners", "ventures", "venture",
    "holdings", "holding", "ai", "io", "inc", "ltd", "llc", "eli", "fox",
    "guild", "honor", "pine", "thrive", "nexus", "alloy", "indigo", "blink",
    "ditto", "boom", "bubble", "button", "cortex", "forge", "human", "light",
    "lunar", "maven", "minimal", "miso", "mistral", "nine", "nox", "odyssey",
    "quantum", "rigetti", "river", "sequoia", "talon", "tomorrow",
    "unframe", "unusual", "uplift", "voxel", "wynn", "yubico",
    "applied", "arch", "armis", "basis", "bessemer", "colossal", "emergence",
    "engine", "flourish", "founders", "iterative", "multiverse",
    "parabilis", "peak", "rocket", "sportradar", "trm", "valor",
    "ww", "charles", "alumni", "baidu", "ditto", "pear",
}


def _normalize(text: str) -> str:
    """Lowercase + strip common corp suffixes + collapse whitespace."""
    base = text.lower().strip()
    for suffix in (
        " inc", " inc.", " corp", " corp.", " corporation", " ltd", " ltd.",
        " llc", " co.", " co", " company", " group", " holdings", " ag",
        " (the)", " the", ",",
    ):
        if base.endswith(suffix):
            base = base[: -len(suffix)].strip()
    base = re.sub(r"\s*\([^)]*\)\s*", " ", base).strip()
    return base


def slug_candidates(name: str, website: str = "") -> list[str]:
    """Generate possible ATS slugs for a company name + website.

    Conservative — generates only slugs we're confident uniquely identify the
    company. Drops the dangerous "first-word" fallback for multi-word names
    (was the major source of false positives like Eli Lilly → "eli").
    """
    cands: set[str] = set()
    base = _normalize(name)
    _words = base.split()  # noqa: F841

    # 1. No-spaces / no-punctuation lowercase — primary slug, always safe to
    #    use even if the result happens to look like a common word (e.g.
    #    "Stytch" → "stytch" is legitimate).
    flat = re.sub(r"[^a-z0-9]+", "", base)
    if flat:
        cands.add(flat)
    # 2. Hyphenated variant
    hyphen = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    if hyphen and hyphen != flat:
        cands.add(hyphen)
    # 3. Website host (only when distinct + non-trivial)
    if website:
        m = re.search(r"https?://(?:www\.)?([a-z0-9-]+)\.", website.lower())
        if m:
            host = m.group(1)
            if len(host) >= 4 and host not in _COMMON_FIRST_WORDS:
                cands.add(host)
    # NOTE: deliberately NO first-word fallback for multi-word names — that
    # was the original false-positive source. For single-word names, the
    # "flat" slug above already IS the single word.
    return [c for c in cands if 3 <= len(c) <= 40]


async def probe_greenhouse(client, slug, sem):
    async with sem:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        try:
            r = await client.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                jobs = data.get("jobs") or []
                if jobs:
                    return ("greenhouse", {"board_token": slug}, len(jobs))
        except Exception:
            pass
    return None


async def probe_lever(client, slug, sem):
    async with sem:
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=1"
        try:
            r = await client.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and data:
                    return ("lever", {"company": slug}, len(data))
        except Exception:
            pass
    return None


async def probe_ashby(client, slug, sem):
    async with sem:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
        try:
            r = await client.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                jobs = data.get("jobs") or []
                if jobs:
                    return ("ashby", {"board_token": slug}, len(jobs))
        except Exception:
            pass
    return None


async def probe_smartrecruiters(client, slug, sem):
    async with sem:
        url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
        try:
            r = await client.get(url, timeout=10, params={"limit": 1})
            if r.status_code == 200:
                data = r.json()
                count = data.get("totalFound") or len(data.get("content") or [])
                if count > 0:
                    return ("smartrecruiters", {"company_id": slug}, count)
        except Exception:
            pass
    return None


async def probe_eightfold(client, slug, sem):
    async with sem:
        url = f"https://{slug}.eightfold.ai/api/pcsx/search"
        try:
            r = await client.get(
                url, timeout=10,
                params={"domain": f"{slug}.com", "start": 0},
            )
            if r.status_code == 200:
                data = r.json()
                api_data = data.get("data") or {}
                count = api_data.get("count") or 0
                if count > 0:
                    return ("eightfold", {"company": slug, "domain": f"{slug}.com"}, count)
        except Exception:
            pass
    return None


async def probe_workday(client, tenant: str, site_id: str, wd_version: str, sem):
    """Probe a Workday CXS endpoint. Requires tenant+site_id+wd_version
    (typically extracted from a *.wd[1-5].myworkdayjobs.com URL we found
    via search). Returns hit on POST with empty filters."""
    async with sem:
        api_url = (
            f"https://{tenant}.wd{wd_version}.myworkdayjobs.com/wday/cxs/"
            f"{tenant}/{site_id}/jobs"
        )
        try:
            # Workday requires a cookie session — GET the page first.
            page_url = f"https://{tenant}.wd{wd_version}.myworkdayjobs.com/en-US/{site_id}"
            await client.get(page_url, timeout=10)
            r = await client.post(
                api_url,
                json={"limit": 1, "offset": 0, "searchText": ""},
                timeout=10,
                headers={"Content-Type": "application/json"},
            )
            if r.status_code == 200:
                data = r.json()
                count = data.get("total") or len(data.get("jobPostings") or [])
                if count > 0:
                    return (
                        "workday",
                        {"tenant": tenant, "site_id": site_id, "wd_version": wd_version},
                        count,
                    )
        except Exception:
            pass
    return None


async def probe_icims(client, slug: str, sem):
    """Probe a public iCIMS career site. Slug is the subdomain part
    (e.g. `careers-acme` from `careers-acme.icims.com`)."""
    async with sem:
        url = f"https://{slug}.icims.com/jobs/search"
        try:
            r = await client.get(url, timeout=10, follow_redirects=True)
            # iCIMS career sites return 200 HTML; 404 if subdomain doesn't exist.
            if r.status_code == 200 and ("icims" in r.url.host.lower() or "icims" in r.text[:5000].lower()):
                return (
                    "icims",
                    {"careers_url": url},
                    # Count not easily knowable without parsing; use 1 as sentinel.
                    1,
                )
        except Exception:
            pass
    return None


PROBES = [
    ("greenhouse", probe_greenhouse),
    ("lever", probe_lever),
    ("ashby", probe_ashby),
    ("smartrecruiters", probe_smartrecruiters),
    ("eightfold", probe_eightfold),
]


async def find_ats_for(client, name: str, website: str, sem: asyncio.Semaphore) -> dict | None:
    """Try every candidate slug × every ATS. Returns first hit or None."""
    cands = slug_candidates(name, website)
    if not cands:
        return None

    # Try longest (most specific) slug first — reduces false-positive matches
    # against short common-word ATS boards.
    cands = sorted(cands, key=len, reverse=True)
    for slug in cands:
        for ats_name, probe_fn in PROBES:
            result = await probe_fn(client, slug, sem)
            if result:
                ats_type, config, job_count = result
                return {
                    "ats": ats_type,
                    "config": config,
                    "job_count": job_count,
                    "matched_slug": slug,
                }
    return None


async def gather_candidates(curated_only: bool = False) -> list[dict]:
    """Pull from all sources, dedupe. Curated list first (highest priority).

    When curated_only=True, skips slow low-yield sources (YC, Crunchbase, Wellfound).
    """
    all_companies: list[dict] = []

    # Curated list of well-known tech companies (highest hit rate)
    for c in fetch_curated():
        all_companies.append(c)

    # Fortune 500
    for c in FORTUNE_500_COMPANIES:
        all_companies.append({
            "name": c["name"],
            "website": "",
            "source": "fortune500",
        })

    if curated_only:
        # Skip YC/CB/Wellfound — too slow and very low hit rate for our ATS set.
        # Dedupe
        seen = {}
        for c in all_companies:
            key = c["name"].lower().strip()
            if key and key not in seen:
                seen[key] = c
        return list(seen.values())

    # YC — accept all active companies with a website
    try:
        yc = await fetch_yc_companies(limit=5000)
        for c in yc:
            all_companies.append({
                "name": c["name"],
                "website": c.get("website", ""),
                "source": "yc",
            })
    except Exception as e:
        logger.error(f"YC fetch failed: {e}")

    # Crunchbase top 5000
    try:
        cb = await fetch_crunchbase_top(limit=5000)
        for c in cb:
            all_companies.append({
                "name": c["name"],
                "website": c.get("website", ""),
                "source": "crunchbase",
            })
    except Exception as e:
        logger.error(f"Crunchbase fetch failed: {e}")

    # Wellfound
    try:
        wf = await fetch_wellfound_companies(limit=300)
        for c in wf:
            all_companies.append({
                "name": c["name"],
                "website": c.get("website", ""),
                "source": "wellfound",
            })
    except Exception as e:
        logger.error(f"Wellfound fetch failed: {e}")

    # Dedupe by lowercase name
    seen = {}
    for c in all_companies:
        key = c["name"].lower().strip()
        if key and key not in seen:
            seen[key] = c
    return list(seen.values())


def name_to_slug(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def existing_slugs() -> set[str]:
    base = pathlib.Path(settings.configs_dir)
    if not base.exists():
        return set()
    return {p.stem for p in base.glob("*.yaml")}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--max", type=int, default=10000)
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--probe-rate", type=int, default=50,
                        help="max concurrent HTTP probes across all ATS endpoints")
    parser.add_argument("--curated-only", action="store_true",
                        help="only probe curated + Fortune 500 sources (skip YC/CB/WF)")
    args = parser.parse_args()

    logger.info("Gathering candidates from all sources...")
    candidates = await gather_candidates(curated_only=args.curated_only)
    logger.info(f"Total unique candidates: {len(candidates)}")
    candidates = candidates[:args.max]

    if args.skip_existing:
        existing = existing_slugs()
        before = len(candidates)
        candidates = [c for c in candidates if name_to_slug(c["name"]) not in existing]
        logger.info(f"Skipped {before - len(candidates)} already-known; processing {len(candidates)}")

    configs_dir = pathlib.Path(settings.configs_dir)
    configs_dir.mkdir(parents=True, exist_ok=True)

    probe_sem = asyncio.Semaphore(args.probe_rate)
    company_sem = asyncio.Semaphore(args.concurrency)

    hits: list[dict] = []
    misses: list[str] = []
    started = time.time()
    done_count = 0

    async with httpx.AsyncClient(
        headers={"User-Agent": UA},
        follow_redirects=True,
    ) as client:
        async def process(c):
            nonlocal done_count
            async with company_sem:
                result = await find_ats_for(client, c["name"], c["website"], probe_sem)
            done_count += 1
            if done_count % 25 == 0:
                elapsed = time.time() - started
                rate = done_count / elapsed if elapsed > 0 else 0
                logger.info(
                    f"  Progress: {done_count}/{len(candidates)} "
                    f"({len(hits)} hits, {done_count - len(hits)} misses)  "
                    f"rate={rate:.1f}/s"
                )
            if not result:
                misses.append(c["name"])
                return

            slug = name_to_slug(c["name"])
            # Canonical schema (matches scripts/normalize_configs.py).
            yaml_data = {
                "name": c["name"],
                "slug": slug,
                "ats": result["ats"],
                "ats_config": result["config"],
                "careers_url": c["website"] or f"https://{result['matched_slug']}.com",
                "verified": True,
                "discovered_from": c["source"],
                "discovered_jobs": int(result["job_count"] or 0),
                "last_verified": time.strftime("%Y-%m-%d", time.gmtime()),
                "evidence_url": None,
            }
            path = configs_dir / f"{slug}.yaml"
            with open(path, "w") as f:
                yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)
            hits.append({**yaml_data, "matched_slug": result["matched_slug"]})

        await asyncio.gather(*(process(c) for c in candidates))

    # Final summary
    print(f"\n{'═' * 70}")
    print(f"  PROBE COMPLETE — {len(candidates)} companies in {time.time()-started:.0f}s")
    print(f"{'═' * 70}")
    print(f"  Hits:   {len(hits)}")
    print(f"  Misses: {len(misses)}")
    print("\nBy ATS:")
    by_ats: dict[str, int] = {}
    for h in hits:
        by_ats[h["ats"]] = by_ats.get(h["ats"], 0) + 1
    for ats, n in sorted(by_ats.items(), key=lambda x: -x[1]):
        print(f"  {ats:<20} {n}")
    print("\nBy source:")
    by_src: dict[str, int] = {}
    for h in hits:
        by_src[h["discovered_from"]] = by_src.get(h["discovered_from"], 0) + 1
    for src, n in sorted(by_src.items(), key=lambda x: -x[1]):
        print(f"  {src:<20} {n}")

    # Save summary
    with open("/tmp/probe_summary.json", "w") as f:
        json.dump({"hits": hits, "miss_count": len(misses), "miss_sample": misses[:30]}, f, indent=2, default=str)
    print("\nSummary at /tmp/probe_summary.json")


if __name__ == "__main__":
    asyncio.run(main())
