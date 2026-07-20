import json
import re

from bs4 import BeautifulSoup

from artemis.core.models import ATSType
from artemis.scrapers.base import BaseScraper, ScrapedJob
from artemis.scrapers.registry import register


@register(ATSType.icims)
class ICIMSScraper(BaseScraper):
    """iCIMS scraper — uses official Search API when customer_id is available,
    falls back to career-site HTML scraping otherwise.

    ats_config options:
      customer_id: iCIMS customer ID (e.g. "1060") — enables Search API
      api_key:     iCIMS API key (basic auth user)
      api_secret:  iCIMS API secret (basic auth pass)
      careers_url: public careers page URL (fallback when no API creds)
    """

    API_BASE = "https://api.icims.com"

    async def scrape(self, query: str, limit: int = 50, skip_detail_urls: set[str] | None = None) -> list[ScrapedJob]:
        customer_id = self.ats_config.get("customer_id")

        # Strategy 1: Official iCIMS Search API (requires customer_id + credentials)
        if customer_id:
            jobs = await self._search_api(customer_id, query, limit)
            if jobs:
                return jobs

        # Strategy 2: Career-site scraping (public, no creds needed)
        careers_url = self.ats_config.get("careers_url", "")
        if not careers_url and not customer_id:
            raise ValueError("iCIMS scraper requires 'customer_id' or 'careers_url' in ats_config")

        if careers_url:
            return await self._scrape_career_site(careers_url, query, limit)

        return []

    # ── Strategy 1: Official Search API ──────────────────────────────────

    async def _search_api(self, customer_id: str, query: str, limit: int) -> list[ScrapedJob]:
        """Use https://api.icims.com/customers/{id}/search/jobs with searchJson."""
        url = f"{self.API_BASE}/customers/{customer_id}/search/jobs"

        search_json = {"filters": [], "operator": "&"}
        if query:
            search_json["filters"].append({
                "name": "job.jobtitle",
                "value": [query],
                "operator": "=",
            })
        # Only return posted jobs
        search_json["filters"].append({
            "name": "job.jobpost.isposted",
            "value": ["1"],
        })

        headers = {"Accept": "application/json"}
        api_key = self.ats_config.get("api_key", "")
        api_secret = self.ats_config.get("api_secret", "")
        if api_key and api_secret:
            import base64
            creds = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
            headers["Authorization"] = f"Basic {creds}"

        jobs = []
        offset = 0
        page_size = 100
        max_pages = 50  # safety cap

        for _ in range(max_pages):
            params = {
                "searchJson": json.dumps(search_json),
                "staleness": "5",
                "count": str(page_size),
                "start": str(offset),
            }

            try:
                response = await self._get(url, params=params, headers=headers)
                data = response.json()
            except Exception:
                break

            results = data.get("searchResults", [])
            if not results:
                break

            for result in results:
                job_id = str(result.get("id", ""))
                self_link = result.get("self", "")
                if not self_link:
                    self_link = f"{self.API_BASE}/customers/{customer_id}/jobs/{job_id}"

                job = await self._fetch_job_detail(self_link, customer_id, job_id, headers)
                if job:
                    jobs.append(job)

            offset += len(results)
            total = data.get("totalCount", data.get("total", 0))
            if total and offset >= total:
                break
            if len(results) < page_size:
                break

        return jobs

    async def _fetch_job_detail(self, api_url: str, customer_id: str, job_id: str, headers: dict) -> ScrapedJob | None:
        """Fetch individual job details from the iCIMS API."""
        try:
            r = await self._get(api_url, headers=headers)
            data = r.json()
        except Exception:
            return None

        title = data.get("jobtitle", data.get("title", ""))
        if not title:
            return None

        location_parts = []
        joblocation = data.get("joblocation", {})
        if isinstance(joblocation, dict):
            addr = joblocation.get("address", joblocation)
            for field in ("addresscity", "addressstate", "addresscountry"):
                val = addr.get(field)
                if val and isinstance(val, str):
                    location_parts.append(val)
                elif val and isinstance(val, dict):
                    location_parts.append(val.get("value", val.get("label", "")))

        return ScrapedJob(
            external_id=job_id,
            title=title,
            url=data.get("directapplyurl", data.get("jobposturl", api_url)),
            location=", ".join(location_parts),
            description=data.get("overview", data.get("responsibilities", "")),
            source="icims_api",
        )

    # ── Strategy 2: Career-site HTML scraping ────────────────────────────

    async def _scrape_career_site(self, careers_url: str, query: str, limit: int) -> list[ScrapedJob]:
        response = await self._get(careers_url, params={"keyword": query} if query else {})
        html = response.text

        jobs = self._extract_from_json_ld(html, careers_url, limit)
        if jobs:
            return jobs

        return self._extract_from_html(html, careers_url, query, limit)

    def _extract_from_json_ld(self, html: str, base_url: str, limit: int) -> list[ScrapedJob]:
        jobs = []
        for match in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL):
            try:
                data = json.loads(match.group(1))
                items = data if isinstance(data, list) else data.get("itemListElement", [data])
                for item in items:
                    if item.get("@type") not in ("JobPosting", "ListItem"):
                        continue
                    posting = item.get("item", item)
                    if posting.get("@type") != "JobPosting":
                        continue
                    title = posting.get("title", "")
                    url = posting.get("url", "")
                    location = ""
                    loc_data = posting.get("jobLocation", {})
                    if isinstance(loc_data, dict):
                        addr = loc_data.get("address", {})
                        location = addr.get("addressLocality", "")

                    jobs.append(ScrapedJob(
                        external_id=posting.get("identifier", {}).get("value", url),
                        title=title,
                        url=url,
                        location=location,
                        description=posting.get("description", ""),
                        source="icims",
                    ))
            except (json.JSONDecodeError, KeyError):
                continue
        return jobs

    def _extract_from_html(self, html: str, base_url: str, query: str, limit: int) -> list[ScrapedJob]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        seen = set()

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if not re.search(r"/jobs?/\d+|/position/|/requisition/", href, re.I):
                continue
            title = link.get_text(strip=True)
            if not title or len(title) < 3:
                continue
            if query and query.lower() not in title.lower():
                continue
            if not href.startswith("http"):
                from urllib.parse import urljoin
                href = urljoin(base_url, href)
            if href in seen:
                continue
            seen.add(href)

            job_id_match = re.search(r"/jobs?/(\d+)", href)
            jobs.append(ScrapedJob(
                external_id=job_id_match.group(1) if job_id_match else href,
                title=title,
                url=href,
                source="icims",
            ))
        return jobs
