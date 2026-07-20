"""
Scrape service — fetches jobs from ATS platforms and upserts to DB.

Used by: worker (async task), CLI (one-shot), API (trigger).
Single source of truth for scrape + upsert logic.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text

from artemis.core.database import async_session
from artemis.core.models import Company, CompanyStatus, Job, ScrapeRun, ScrapeRunStatus
from artemis.scrapers.registry import get_scraper

logger = logging.getLogger("artemis.services.scrape")


async def scrape_company(company_id: str, query: str = "", limit: int = 0) -> dict:
    """
    Scrape ALL jobs for a company, upsert to DB with delta tracking.
    limit=0 means no limit (fetch everything).

    Returns: {"jobs_found": int, "jobs_new": int, "jobs_updated": int, "new_job_ids": list[UUID]}
    """
    async with async_session() as session:
        result = await session.execute(select(Company).where(Company.id == uuid.UUID(company_id)))
        company = result.scalar_one_or_none()
        if not company:
            raise ValueError(f"Company {company_id} not found")

        run = ScrapeRun(company_id=company.id, status=ScrapeRunStatus.running)
        session.add(run)
        await session.commit()

        try:
            scraper = get_scraper(company.ats_type, company.ats_config)
            effective_limit = limit if limit > 0 else 10000

            # Pre-load URLs for jobs we already have descriptions for, so the
            # scraper can skip expensive per-job detail fetches (e.g. Eightfold).
            existing_with_desc = await session.execute(
                text(
                    "SELECT url FROM jobs "
                    "WHERE company_id = :cid AND description IS NOT NULL AND length(description) > 100"
                ),
                {"cid": company.id},
            )
            skip_detail_urls = {row[0] for row in existing_with_desc.all()}

            async with scraper:
                scraped = await scraper.scrape(
                    query=query,
                    limit=effective_limit,
                    skip_detail_urls=skip_detail_urls,
                )

            new_job_ids = []
            updated_count = 0
            seen_urls = set()

            for sj in scraped:
                if sj.url in seen_urls:
                    continue
                seen_urls.add(sj.url)

                # Rule-based normalization
                from artemis.normalizer.rules import normalize_job_rules

                normalized = normalize_job_rules(
                    sj.title,
                    sj.location or "",
                    sj.description or "",
                    ats_metadata=sj.metadata,
                )

                # Check if job exists for delta tracking
                existing = await session.execute(select(Job).where(Job.url == sj.url))
                existing_job = existing.scalar_one_or_none()

                if existing_job:
                    # Track changes
                    changes = []
                    if existing_job.title != sj.title:
                        changes.append(("title", existing_job.title, sj.title))
                    if existing_job.location != sj.location:
                        changes.append(("location", existing_job.location, sj.location))
                    if existing_job.description and sj.description and existing_job.description != sj.description:
                        changes.append(("description", "changed", "updated"))

                    for field, old, new in changes:
                        await session.execute(
                            text(
                                "INSERT INTO job_changes (job_id, change_type, field_name, old_value, new_value) VALUES (:jid, 'updated', :field, :old, :new)"
                            ),
                            {"jid": existing_job.id, "field": field, "old": str(old)[:500], "new": str(new)[:500]},
                        )
                        updated_count += 1

                    # Update existing job
                    existing_job.last_seen_at = datetime.now(timezone.utc)
                    existing_job.is_active = True
                    if sj.title != existing_job.title:
                        existing_job.title = sj.title
                    if sj.location != existing_job.location:
                        existing_job.location = sj.location
                    # Update description if the scraped value is non-empty (lets us
                    # backfill jobs that were created before description fetching worked).
                    if sj.description and sj.description != existing_job.description:
                        existing_job.description = sj.description
                    if sj.date_posted and sj.date_posted != existing_job.date_posted:
                        existing_job.date_posted = sj.date_posted
                    existing_job.metadata_ = normalized
                    existing_job.normalized_at = datetime.now(timezone.utc)
                    if normalized.get("salary_min"):
                        existing_job.salary_min = normalized["salary_min"]
                    if normalized.get("salary_max"):
                        existing_job.salary_max = normalized["salary_max"]
                    if normalized.get("visa_sponsorship") is not None:
                        existing_job.visa_sponsorship = normalized["visa_sponsorship"]
                else:
                    # Insert new job
                    new_job = Job(
                        id=uuid.uuid4(),
                        external_id=sj.external_id,
                        company_id=company.id,
                        title=sj.title,
                        url=sj.url,
                        location=sj.location,
                        description=sj.description,
                        date_posted=sj.date_posted,
                        source=sj.source,
                        is_active=True,
                        metadata_=normalized,
                        normalized_at=datetime.now(timezone.utc),
                        salary_min=normalized.get("salary_min"),
                        salary_max=normalized.get("salary_max"),
                        visa_sponsorship=normalized.get("visa_sponsorship"),
                    )
                    session.add(new_job)
                    await session.flush()
                    new_job_ids.append(new_job.id)

                    # Track as new
                    await session.execute(
                        text(
                            "INSERT INTO job_changes (job_id, change_type, field_name) VALUES (:jid, 'created', 'job')"
                        ),
                        {"jid": new_job.id},
                    )

            # Mark jobs NOT seen in this scrape as potentially closed
            if scraped:
                scraped_urls = {sj.url for sj in scraped}
                existing_active = await session.execute(
                    select(Job).where(Job.company_id == company.id, Job.is_active.is_(True))
                )
                for job in existing_active.scalars():
                    if job.url not in scraped_urls:
                        job.is_active = False
                        await session.execute(
                            text(
                                "INSERT INTO job_changes (job_id, change_type, field_name, old_value, new_value) VALUES (:jid, 'closed', 'is_active', 'true', 'false')"
                            ),
                            {"jid": job.id},
                        )

            company.last_scraped_at = datetime.now(timezone.utc)
            run.status = ScrapeRunStatus.success
            run.jobs_found = len(scraped)
            run.jobs_new = len(new_job_ids)
            run.completed_at = datetime.now(timezone.utc)
            await session.commit()

            return {
                "company_slug": company.slug,
                "jobs_found": len(scraped),
                "jobs_new": len(new_job_ids),
                "jobs_updated": updated_count,
                "new_job_ids": new_job_ids,
            }

        except Exception as e:
            run.status = ScrapeRunStatus.failed
            run.error_message = str(e)
            run.completed_at = datetime.now(timezone.utc)
            await session.commit()
            raise


async def scrape_all(query: str = "") -> list[dict]:
    """Scrape all active companies. Returns list of per-company results."""
    async with async_session() as session:
        result = await session.execute(select(Company).where(Company.status == CompanyStatus.active))
        companies = result.scalars().all()

    results = []
    for company in companies:
        try:
            r = await scrape_company(str(company.id), query=query)
            results.append(r)
        except Exception as e:
            logger.error(f"Failed to scrape {company.slug}: {e}")
            results.append({"company_slug": company.slug, "error": str(e)})
    return results
