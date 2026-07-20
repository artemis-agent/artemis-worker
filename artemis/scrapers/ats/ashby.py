from artemis.core.models import ATSType
from artemis.scrapers.base import BaseScraper, ScrapedJob
from artemis.scrapers.registry import register


@register(ATSType.ashby)
class AshbyScraper(BaseScraper):
    """Ashby posting API: GET api.ashbyhq.com/posting-api/job-board/{board_token}"""

    async def scrape(self, query: str, limit: int = 50, skip_detail_urls: set[str] | None = None) -> list[ScrapedJob]:
        token = self.ats_config.get("board_token", "")
        if not token:
            raise ValueError("Ashby scraper requires 'board_token' in ats_config")

        url = f"https://api.ashbyhq.com/posting-api/job-board/{token}"
        response = await self._get(url)
        data = response.json()

        jobs = []
        for item in data.get("jobs", []):
            title = item.get("title", "")
            if query and query.lower() not in title.lower():
                continue

            locations = []
            primary_loc = item.get("location")
            if primary_loc:
                locations.append(primary_loc)
            for sec in item.get("secondaryLocations", []):
                if isinstance(sec, dict):
                    locations.append(sec.get("locationName", ""))
                elif isinstance(sec, str):
                    locations.append(sec)

            date_posted = None
            published = item.get("publishedAt")
            if published:
                from dateutil.parser import parse as parse_date
                try:
                    date_posted = parse_date(published)
                except (ValueError, TypeError):
                    pass

            # Use descriptionPlain (lighter) over descriptionHtml when available
            description = item.get("descriptionPlain") or item.get("descriptionHtml", "")

            jobs.append(ScrapedJob(
                external_id=str(item.get("id", "")),
                title=title,
                url=item.get("jobUrl", ""),
                location=", ".join(locations),
                description=description[:2000] if description else "",
                date_posted=date_posted,
                source="ashby",
                metadata={
                    "department": item.get("department", ""),
                    "team": item.get("team", ""),
                    "employment_type": item.get("employmentType", ""),
                    "is_remote": item.get("isRemote", False),
                    "compensation": item.get("compensationTierSummary", ""),
                },
            ))


        return jobs
