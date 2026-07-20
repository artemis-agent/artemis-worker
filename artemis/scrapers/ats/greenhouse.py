from artemis.core.models import ATSType
from artemis.scrapers.base import BaseScraper, ScrapedJob
from artemis.scrapers.registry import register


@register(ATSType.greenhouse)
class GreenhouseScraper(BaseScraper):
    """Greenhouse boards API: GET boards-api.greenhouse.io/v1/boards/{token}/jobs"""

    async def scrape(self, query: str, limit: int = 50, skip_detail_urls: set[str] | None = None) -> list[ScrapedJob]:
        token = self.ats_config.get("board_token", "")
        if not token:
            raise ValueError("Greenhouse scraper requires 'board_token' in ats_config")

        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
        params = {"content": "true"}
        response = await self._get(url, params=params)
        data = response.json()

        jobs = []
        for item in data.get("jobs", []):
            title = item.get("title", "")
            if query and query.lower() not in title.lower():
                continue

            location = item.get("location", {}).get("name", "")
            job_url = item.get("absolute_url", "")
            content = item.get("content", "")

            date_posted = None
            updated_at = item.get("updated_at")
            if updated_at:
                from dateutil.parser import parse as parse_date

                try:
                    date_posted = parse_date(updated_at)
                except (ValueError, TypeError):
                    pass

            # Extract structured metadata from API
            departments = [d.get("name", "") for d in item.get("departments", [])]
            offices = [o.get("name", "") for o in item.get("offices", [])]

            jobs.append(
                ScrapedJob(
                    external_id=str(item.get("id", "")),
                    title=title,
                    url=job_url,
                    location=location,
                    description=content,
                    date_posted=date_posted,
                    source="greenhouse",
                    metadata={
                        "department": departments[0] if departments else "",
                        "offices": offices,
                        "employment_type": item.get("employment_type", ""),
                    },
                )
            )

        return jobs
