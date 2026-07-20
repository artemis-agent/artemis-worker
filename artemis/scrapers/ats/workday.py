from artemis.core.models import ATSType
from artemis.scrapers.base import BaseScraper, ScrapedJob
from artemis.scrapers.registry import register


@register(ATSType.workday)
class WorkdayScraper(BaseScraper):
    """Workday CXS API — requires cookie session via initial page GET."""

    async def scrape(self, query: str, limit: int = 50, skip_detail_urls: set[str] | None = None) -> list[ScrapedJob]:
        tenant = self.ats_config.get("tenant", "")
        site_id = self.ats_config.get("site_id", "External_Career_Site")
        wd_version = self.ats_config.get("wd_version", "5")
        if not tenant:
            raise ValueError("Workday scraper requires 'tenant' in ats_config")

        base_host = f"https://{tenant}.wd{wd_version}.myworkdayjobs.com"
        page_url = f"{base_host}/en-US/{site_id}"
        api_url = f"{base_host}/wday/cxs/{tenant}/{site_id}/jobs"
        job_base_url = f"{base_host}/{site_id}"

        # Step 1: GET the career page to establish a cookie session
        # Workday requires PLAY_SESSION + CALYPSO_CSRF_TOKEN cookies
        await self._get(page_url)

        # Step 2: POST to CXS API (cookies are carried by httpx client)
        jobs = []
        offset = 0

        while True:
            payload = {
                "appliedFacets": {},
                "limit": 20,
                "offset": offset,
                "searchText": query,
            }
            response = await self._post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            data = response.json()
            items = data.get("jobPostings", [])
            if not items:
                break

            for item in items:
                external_path = item.get("externalPath", "")
                bullet_fields = item.get("bulletFields", [])

                jobs.append(ScrapedJob(
                    external_id=bullet_fields[0] if bullet_fields else external_path,
                    title=item.get("title", ""),
                    url=f"{job_base_url}{external_path}",
                    location=item.get("locationsText", ""),
                    description=bullet_fields[0] if bullet_fields else "",
                    date_posted=None,
                    source="workday",
                ))

            offset += len(items)
            total = data.get("total", 0)
            if offset >= total:
                break

        return jobs
