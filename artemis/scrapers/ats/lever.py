import re

from artemis.core.models import ATSType
from artemis.scrapers.base import BaseScraper, ScrapedJob
from artemis.scrapers.registry import register


@register(ATSType.lever)
class LeverScraper(BaseScraper):
    """Lever postings API: GET api.lever.co/v0/postings/{company}"""

    async def scrape(self, query: str, limit: int = 50, skip_detail_urls: set[str] | None = None) -> list[ScrapedJob]:
        company = self.ats_config.get("company", "")
        if not company:
            raise ValueError("Lever scraper requires 'company' in ats_config")

        # Try JSON API first
        jobs = await self._try_json_api(company, query, limit)
        if jobs:
            return jobs

        # Fallback: scrape the HTML listing page
        return await self._scrape_html(company, query, limit)

    async def _try_json_api(self, company: str, query: str, limit: int) -> list[ScrapedJob]:
        url = f"https://api.lever.co/v0/postings/{company}"
        jobs = []
        skip = 0
        page_size = 100
        max_pages = 50

        for _ in range(max_pages):
            params = {"mode": "json", "limit": page_size, "skip": skip}
            try:
                response = await self._get(url, params=params)
            except Exception:
                break

            data = response.json()
            if not isinstance(data, list) or not data:
                break

            for item in data:
                title = item.get("text", "")
                if query and query.lower() not in title.lower():
                    continue

                categories = item.get("categories", {})
                all_locs = categories.get("allLocations", [])
                location = categories.get("location", "") or (all_locs[0] if all_locs else "")

                date_posted = None
                created_at = item.get("createdAt")
                if created_at:
                    from datetime import datetime

                    try:
                        date_posted = datetime.fromtimestamp(created_at / 1000)
                    except (ValueError, TypeError, OSError):
                        pass

                description_parts = []
                for lst in item.get("lists", []):
                    description_parts.append(lst.get("text", ""))
                    for li in lst.get("content", "").split("<li>"):
                        clean = li.replace("</li>", "").strip()
                        if clean:
                            description_parts.append(f"- {clean}")

                categories = item.get("categories", {})

                jobs.append(
                    ScrapedJob(
                        external_id=item.get("id", ""),
                        title=title,
                        url=item.get("hostedUrl", ""),
                        location=location,
                        description="\n".join(description_parts),
                        date_posted=date_posted,
                        source="lever",
                        metadata={
                            "department": categories.get("department", ""),
                            "team": categories.get("team", ""),
                            "commitment": categories.get("commitment", ""),
                            "workplace_type": categories.get("workplaceType", ""),
                            "all_locations": categories.get("allLocations", []),
                        },
                    )
                )

            if len(data) < page_size:
                break  # last page
            skip += len(data)

        return jobs

    async def _scrape_html(self, company: str, query: str, limit: int) -> list[ScrapedJob]:
        """Fallback: scrape jobs.lever.co/{company} HTML page."""
        url = f"https://jobs.lever.co/{company}"
        try:
            response = await self._get(url)
        except Exception:
            return []

        jobs = []
        seen = set()
        # Lever HTML uses pattern: /company/job-id
        for match in re.finditer(
            rf'href="(https://jobs\.lever\.co/{re.escape(company)}/([a-f0-9-]+))"[^>]*>\s*<[^>]*>([^<]+)',
            response.text,
            re.I,
        ):
            job_url, job_id, title = match.group(1), match.group(2), match.group(3).strip()
            if job_id in seen or not title:
                continue
            if query and query.lower() not in title.lower():
                continue
            seen.add(job_id)
            jobs.append(
                ScrapedJob(
                    external_id=job_id,
                    title=title,
                    url=job_url,
                    source="lever",
                )
            )
            if len(jobs) >= limit:
                break
        return jobs
