"""Eightfold ATS scraper.

The Eightfold PCSX list endpoint (`/api/pcsx/search`) returns only minimal
fields per position — no description, no employment type, no salary. We have
to fetch each job's detail page (`/careers/job/{id}`) and parse the embedded
JSON-LD `JobPosting` block to get the rich content.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone

import httpx

from artemis.core.models import ATSType
from artemis.scrapers.base import BaseScraper, ScrapedJob
from artemis.scrapers.registry import register

logger = logging.getLogger("artemis.scrapers.eightfold")

# Limit concurrent detail fetches per scrape — Eightfold detail pages are large
# (~700KB HTML each), so we cap to avoid hammering their CDN.
DETAIL_CONCURRENCY = 8
DETAIL_TIMEOUT = 20.0

# Extract <script type="application/ld+json">...</script> from job detail HTML
_JSONLD_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.+?)</script>',
    re.DOTALL,
)


@register(ATSType.eightfold)
class EightfoldScraper(BaseScraper):
    """Eightfold PCSX API: lists jobs then fetches per-job detail JSON-LD."""

    async def scrape(
        self,
        query: str,
        limit: int = 50,
        skip_detail_urls: set[str] | None = None,
    ) -> list[ScrapedJob]:
        """Scrape jobs.

        Args:
            query: search query (passed through to Eightfold's API)
            limit: max jobs to return (0 = no limit)
            skip_detail_urls: URLs of jobs we ALREADY have full descriptions for.
                Skipping these saves ~70% of scrape time on re-scrapes since the
                detail HTML is the slow part (~700KB each, no API alternative).
        """
        company = self.ats_config.get("company", "")
        domain = self.ats_config.get("domain", f"{company}.com")
        if not company:
            raise ValueError("Eightfold scraper requires 'company' in ats_config")

        skip_set = skip_detail_urls or set()

        base_host = f"https://{company}.eightfold.ai"
        base_url = f"{base_host}/api/pcsx/search"
        all_jobs: list[ScrapedJob] = []
        start = 0
        max_pages = 500  # safety cap (5000 jobs)
        # Eightfold's API ignores page-size params and always returns ~10 per page
        # — we paginate purely by incrementing `start`. Stop once we reach `limit`.

        # ── Step 1: list pages ──
        for _ in range(max_pages):
            params = {
                "domain": domain,
                "query": query,
                "start": start,
                "sort_by": "relevance",
            }
            response = await self._get(base_url, params=params)
            data = response.json()
            api_data = data.get("data", {})
            positions = api_data.get("positions", [])
            total_count = api_data.get("count", 0)
            if not positions:
                break

            for item in positions:
                all_jobs.append(self._build_basic_job(item, base_host))

            start += len(positions)
            if limit and len(all_jobs) >= limit:
                all_jobs = all_jobs[:limit]
                break
            if total_count and start >= total_count:
                break

        # ── Step 2: enrich with descriptions from detail pages ──
        # Only fetch detail for jobs we don't already have descriptions for.
        # The list endpoint returns no description, and Eightfold doesn't expose a
        # bulk-detail API — each detail is a 200-700KB server-rendered HTML page
        # with a JSON-LD JobPosting block (schema.org standard). This is the only
        # available source for description / employmentType / validThrough.
        needs_detail = [j for j in all_jobs if j.url not in skip_set]
        if needs_detail:
            await self._enrich_descriptions(needs_detail)
            if skip_set:
                logger.info(
                    f"eightfold: enriched {len(needs_detail)} new jobs, "
                    f"skipped {len(all_jobs) - len(needs_detail)} already-cached"
                )

        return all_jobs

    def _build_basic_job(self, item: dict, base_host: str) -> ScrapedJob:
        """Build a ScrapedJob from a single list-API position record."""
        job_id = str(item.get("id", ""))
        display_id = item.get("displayJobId") or job_id

        # Locations: prefer standardized over raw
        std_locs = item.get("standardizedLocations") or []
        raw_locs = item.get("locations") or []
        loc_list = std_locs if std_locs else raw_locs
        location = " | ".join(loc_list) if isinstance(loc_list, list) else str(loc_list)

        # postedTs is a Unix epoch int, NOT a parseable string
        date_posted: datetime | None = None
        posted_ts = item.get("postedTs")
        if isinstance(posted_ts, (int, float)) and posted_ts > 0:
            try:
                date_posted = datetime.fromtimestamp(posted_ts, tz=timezone.utc)
            except (ValueError, OSError):
                pass

        # URL — list response has positionUrl (relative path)
        raw_url = item.get("canonicalPositionUrl") or item.get("positionUrl") or ""
        if raw_url and not raw_url.startswith("http"):
            raw_url = f"{base_host}{raw_url}"
        if not raw_url:
            raw_url = f"{base_host}/careers/job/{job_id}"

        # workLocationOption: "onsite" | "remote" | "hybrid"
        work_loc = (item.get("workLocationOption") or "").lower()

        return ScrapedJob(
            external_id=job_id,
            title=item.get("name", "Unknown"),
            url=raw_url,
            location=location,
            description="",  # filled in by _enrich_descriptions
            date_posted=date_posted,
            source="eightfold",
            metadata={
                "display_job_id": display_id,
                "department": item.get("department", ""),
                "team": item.get("team", ""),
                "workplace_type": work_loc,
                "is_remote": work_loc == "remote",
                "ats_job_id": item.get("atsJobId", ""),
            },
        )

    async def _enrich_descriptions(self, jobs: list[ScrapedJob]):
        """Fetch detail HTML for each job and extract JSON-LD description.

        Runs in parallel with a semaphore. Failures are non-fatal — the job
        keeps its empty description rather than dropping out of the result.
        """
        sem = asyncio.Semaphore(DETAIL_CONCURRENCY)
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(DETAIL_TIMEOUT),
            follow_redirects=True,
            headers={"User-Agent": "Artemis/1.0 (+https://artemis.jobs)"},
        ) as client:
            tasks = [self._fetch_one(client, sem, j) for j in jobs]
            await asyncio.gather(*tasks, return_exceptions=True)

        # Report how many succeeded
        filled = sum(1 for j in jobs if j.description)
        logger.info(f"eightfold: enriched {filled}/{len(jobs)} job descriptions")

    async def _fetch_one(
        self,
        client: httpx.AsyncClient,
        sem: asyncio.Semaphore,
        job: ScrapedJob,
    ):
        async with sem:
            try:
                r = await client.get(job.url)
                if r.status_code != 200:
                    return
                jsonld = self._extract_jsonld(r.text)
                if not jsonld:
                    return

                desc = jsonld.get("description") or ""
                if desc:
                    job.description = desc[:10000]  # cap to keep DB row size sane

                # Use JSON-LD employmentType (more accurate than the list endpoint)
                emp_type = jsonld.get("employmentType")
                if emp_type:
                    if isinstance(emp_type, list):
                        emp_type = emp_type[0] if emp_type else ""
                    job.metadata["employment_type"] = _normalize_employment_type(emp_type)

                # validThrough → closing date (optional)
                if jsonld.get("validThrough"):
                    job.metadata["valid_through"] = jsonld["validThrough"]

                # Refine location from JSON-LD if list endpoint had nothing
                if not job.location and jsonld.get("jobLocation"):
                    job.location = _extract_jsonld_location(jsonld["jobLocation"])

                # Hiring organization
                hiring_org = jsonld.get("hiringOrganization") or {}
                if isinstance(hiring_org, dict) and hiring_org.get("name"):
                    job.metadata["hiring_org"] = hiring_org["name"]

            except Exception as e:
                logger.debug(f"eightfold detail fetch failed for {job.url}: {e}")

    @staticmethod
    def _extract_jsonld(html: str) -> dict | None:
        """Extract the JobPosting JSON-LD block from a detail page."""
        for block in _JSONLD_RE.findall(html):
            try:
                obj = json.loads(block)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, list):
                obj = next(
                    (o for o in obj if isinstance(o, dict) and o.get("@type") == "JobPosting"),
                    None,
                )
            if isinstance(obj, dict) and obj.get("@type") == "JobPosting":
                return obj
        return None


def _normalize_employment_type(et: str) -> str:
    """Convert schema.org employment types to readable form."""
    et = (et or "").upper().replace("_", "-")
    return {
        "FULL-TIME": "Full-time",
        "PART-TIME": "Part-time",
        "CONTRACTOR": "Contract",
        "TEMPORARY": "Temporary",
        "INTERN": "Internship",
        "VOLUNTEER": "Volunteer",
        "PER-DIEM": "Per-diem",
        "OTHER": "Other",
    }.get(et, et.title())


def _extract_jsonld_location(loc) -> str:
    """Turn jobLocation (dict or list of dicts) into a readable string."""
    if isinstance(loc, list):
        return " | ".join(filter(None, (_extract_jsonld_location(loc) for loc in loc)))
    if not isinstance(loc, dict):
        return ""
    addr = loc.get("address") or {}
    if not isinstance(addr, dict):
        return ""
    parts = [
        addr.get("addressLocality"),
        addr.get("addressRegion"),
        addr.get("addressCountry"),
    ]
    return ", ".join(p for p in parts if p)
