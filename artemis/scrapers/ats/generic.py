import re

from bs4 import BeautifulSoup

from artemis.core.models import ATSType
from artemis.scrapers.base import BaseScraper, ScrapedJob
from artemis.scrapers.registry import register


@register(ATSType.custom)
class GenericScraper(BaseScraper):
    """Fallback scraper: fetches careers page HTML and extracts job links heuristically."""

    JOB_PATH_PATTERNS = re.compile(
        r"/(job|jobs|position|positions|opening|openings|career|careers|posting|postings|vacancy|vacancies)"
        r"/[^\"'\s#?]+",
        re.IGNORECASE,
    )

    async def scrape(self, query: str, limit: int = 50, skip_detail_urls: set[str] | None = None) -> list[ScrapedJob]:
        careers_url = self.ats_config.get("careers_url", "")
        if not careers_url:
            raise ValueError("Generic scraper requires 'careers_url' in ats_config")

        # Try JSON API detection first
        jobs = await self._try_json_api(careers_url, query, limit)
        if jobs:
            return jobs

        # Fall back to HTML scraping
        return await self._scrape_html(careers_url, query, limit)

    async def _try_json_api(self, careers_url: str, query: str, limit: int) -> list[ScrapedJob]:
        """Try common SPA API endpoint patterns."""
        from urllib.parse import urlparse

        parsed = urlparse(careers_url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        api_patterns = [
            f"{base}/api/jobs?q={query}",
            f"{base}/api/careers/jobs?keyword={query}",
            f"{base}/api/v1/jobs?search={query}",
        ]

        for api_url in api_patterns:
            try:
                response = await self._get(api_url)
                data = response.json()
                if isinstance(data, dict) and ("jobs" in data or "results" in data or "data" in data):
                    items = data.get("jobs") or data.get("results") or data.get("data", [])
                    if isinstance(items, list) and items:
                        return self._parse_generic_json(items, base, limit)
            except Exception:
                continue
        return []

    def _parse_generic_json(self, items: list, base_url: str, limit: int) -> list[ScrapedJob]:
        jobs = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = item.get("title") or item.get("name") or item.get("jobTitle") or ""
            url = item.get("url") or item.get("absolute_url") or item.get("link") or ""
            if url and not url.startswith("http"):
                url = f"{base_url}{url}"
            job_id = str(item.get("id") or item.get("jobId") or item.get("requisitionId") or url)

            jobs.append(
                ScrapedJob(
                    external_id=job_id,
                    title=title,
                    url=url,
                    location=str(item.get("location") or item.get("locationName") or ""),
                    description=str(item.get("description") or item.get("shortDescription") or ""),
                    source="generic_api",
                )
            )
        return jobs

    async def _scrape_html(self, careers_url: str, query: str, limit: int) -> list[ScrapedJob]:
        response = await self._get(careers_url)
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove non-content elements
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        jobs = []
        seen_urls = set()

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if not self.JOB_PATH_PATTERNS.search(href):
                continue

            title = link.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            if query and query.lower() not in title.lower():
                continue

            if not href.startswith("http"):
                from urllib.parse import urljoin

                href = urljoin(careers_url, href)

            if href in seen_urls:
                continue
            seen_urls.add(href)

            jobs.append(
                ScrapedJob(
                    external_id=href,
                    title=title,
                    url=href,
                    source="generic_html",
                )
            )

        return jobs
