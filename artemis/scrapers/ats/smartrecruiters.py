from artemis.core.models import ATSType
from artemis.scrapers.base import BaseScraper, ScrapedJob
from artemis.scrapers.registry import register


@register(ATSType.smartrecruiters)
class SmartRecruitersScraper(BaseScraper):
    """SmartRecruiters API: GET api.smartrecruiters.com/v1/companies/{company_id}/postings"""

    async def scrape(self, query: str, limit: int = 50, skip_detail_urls: set[str] | None = None) -> list[ScrapedJob]:
        company_id = self.ats_config.get("company_id", "")
        if not company_id:
            raise ValueError("SmartRecruiters scraper requires 'company_id' in ats_config")

        base_url = f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings"
        jobs = []
        offset = 0

        while len(jobs) < limit:
            params = {"q": query, "offset": offset, "limit": 100}
            response = await self._get(base_url, params=params)
            data = response.json()
            items = data.get("content", [])
            if not items:
                break

            for item in items:
                title = item.get("name", "")
                if query and query.lower() not in title.lower():
                    continue

                ref = item.get("ref", "")
                location = item.get("location", {})
                loc_parts = [location.get("city", ""), location.get("region", ""), location.get("country", "")]
                loc_str = ", ".join(p for p in loc_parts if p)

                date_posted = None
                released = item.get("releasedDate")
                if released:
                    from dateutil.parser import parse as parse_date
                    try:
                        date_posted = parse_date(released)
                    except (ValueError, TypeError):
                        pass

                company_info = item.get("company", {})
                job_url = f"https://jobs.smartrecruiters.com/{company_id}/{ref}" if ref else ""

                jobs.append(ScrapedJob(
                    external_id=item.get("id", ref),
                    title=title,
                    url=job_url,
                    location=loc_str,
                    description=item.get("name", ""),
                    date_posted=date_posted,
                    source="smartrecruiters",
                    metadata={
                        "department": item.get("department", {}).get("label", ""),
                        "employment_type": item.get("typeOfEmployment", {}).get("label", ""),
                        "experience_level": item.get("experienceLevel", {}).get("label", ""),
                    },
                ))

            offset += len(items)
            total = data.get("totalFound", 0)
            if offset >= total:
                break

        return jobs
