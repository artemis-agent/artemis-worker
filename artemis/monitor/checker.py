"""
ATS-aware job liveness checker.

Primary strategy: call each ATS's single-job API endpoint (fast, structured JSON).
Fallback: HTTP GET the stored job URL and check status code / body text.
"""

import asyncio
import logging
import random
import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

import httpx

from artemis.core.models import ATSType
from artemis.scrapers.base import USER_AGENTS

logger = logging.getLogger("artemis.monitor")
# Patterns that indicate a job has been removed (case-insensitive)
INACTIVE_TEXT_PATTERNS = [
    r"no longer (available|accepting)",
    r"position has been (filled|closed)",
    r"this job (has been|is) (removed|closed|filled|no longer)",
    r"job (not|no longer) found",
    r"this posting has (expired|been removed)",
    r"sorry.{0,30}(position|job|role).{0,30}(no longer|not) available",
]
_INACTIVE_RE = re.compile("|".join(INACTIVE_TEXT_PATTERNS), re.IGNORECASE)


class CheckResult(str, Enum):
    OK = "ok"
    INACTIVE = "inactive"
    ERROR = "error"


@dataclass
class JobCheckItem:
    job_id: str
    external_id: str | None
    url: str
    ats_type: str
    ats_config: dict
    company_slug: str


@dataclass
class JobCheckResult:
    job_id: str
    status: CheckResult
    detail: str = ""


async def check_jobs(
    jobs: list[JobCheckItem],
    concurrency_per_domain: int = 5,
) -> list[JobCheckResult]:
    """Check a batch of jobs grouped by company for liveness."""
    # Group by company_slug to apply per-domain concurrency
    by_company: dict[str, list[JobCheckItem]] = {}
    for job in jobs:
        by_company.setdefault(job.company_slug, []).append(job)

    all_results: list[JobCheckResult] = []
    tasks = []

    async with httpx.AsyncClient(
        headers={"User-Agent": random.choice(USER_AGENTS)},
        timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0),
        follow_redirects=False,
    ) as client:
        for slug, company_jobs in by_company.items():
            sem = asyncio.Semaphore(concurrency_per_domain)
            for job in company_jobs:
                tasks.append(_check_one(client, sem, job))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"check failed: {r}")
            elif r is not None:
                all_results.append(r)

    return all_results


async def _check_one(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    job: JobCheckItem,
) -> JobCheckResult:
    """Check a single job, trying ATS API first then URL fallback."""
    async with sem:
        try:
            ats = ATSType(job.ats_type) if job.ats_type else None
        except ValueError:
            ats = None

        # Try ATS-specific API first
        if ats and job.external_id:
            try:
                result = await _check_via_ats_api(client, ats, job)
                if result is not None:
                    return result
            except Exception as e:
                logger.debug(f"ATS API check failed for {job.job_id}, falling back to URL: {e}")

        # Fallback: check the stored URL directly
        try:
            return await _check_via_url(client, job)
        except Exception as e:
            return JobCheckResult(job_id=job.job_id, status=CheckResult.ERROR, detail=str(e))


async def _check_via_ats_api(
    client: httpx.AsyncClient,
    ats: ATSType,
    job: JobCheckItem,
) -> JobCheckResult | None:
    """Check job via ATS-specific single-job API. Returns None if unsupported."""
    config = job.ats_config or {}

    if ats == ATSType.greenhouse:
        token = config.get("board_token", config.get("company", ""))
        if not token:
            return None
        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job.external_id}"
        resp = await client.get(url)
        if resp.status_code == 404:
            return JobCheckResult(job.job_id, CheckResult.INACTIVE, "greenhouse 404")
        if resp.status_code == 200:
            return JobCheckResult(job.job_id, CheckResult.OK, "greenhouse 200")
        return None  # unexpected status, fall through to URL check

    elif ats == ATSType.lever:
        company = config.get("company", "")
        if not company:
            return None
        url = f"https://api.lever.co/v0/postings/{company}/{job.external_id}?mode=json"
        resp = await client.get(url)
        if resp.status_code == 404:
            return JobCheckResult(job.job_id, CheckResult.INACTIVE, "lever 404")
        if resp.status_code == 200:
            return JobCheckResult(job.job_id, CheckResult.OK, "lever 200")
        return None

    elif ats == ATSType.ashby:
        token = config.get("board_token", config.get("company", ""))
        if not token:
            return None
        url = f"https://api.ashbyhq.com/posting-api/job-board/{token}"
        resp = await client.get(url)
        if resp.status_code != 200:
            return None
        try:
            data = resp.json()
            job_ids = {str(j.get("id", "")) for j in data.get("jobs", [])}
            if job.external_id in job_ids:
                return JobCheckResult(job.job_id, CheckResult.OK, "ashby listed")
            return JobCheckResult(job.job_id, CheckResult.INACTIVE, "ashby not in listing")
        except Exception:
            return None

    elif ats == ATSType.smartrecruiters:
        company_id = config.get("company_id", config.get("company", ""))
        if not company_id:
            return None
        url = f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings/{job.external_id}"
        resp = await client.get(url)
        if resp.status_code == 404:
            return JobCheckResult(job.job_id, CheckResult.INACTIVE, "smartrecruiters 404")
        if resp.status_code == 200:
            return JobCheckResult(job.job_id, CheckResult.OK, "smartrecruiters 200")
        return None

    elif ats == ATSType.icims:
        customer_id = config.get("customer_id", "")
        if not customer_id:
            return None
        url = f"https://api.icims.com/customers/{customer_id}/jobs/{job.external_id}"
        resp = await client.get(url)
        if resp.status_code == 404:
            return JobCheckResult(job.job_id, CheckResult.INACTIVE, "icims 404")
        if resp.status_code == 200:
            return JobCheckResult(job.job_id, CheckResult.OK, "icims 200")
        return None

    elif ats in (ATSType.eightfold, ATSType.workday):
        # These ATS platforms don't have a clean single-job JSON API.
        # Fall through to URL-based check.
        return None

    return None  # unknown ATS


async def _check_via_url(client: httpx.AsyncClient, job: JobCheckItem) -> JobCheckResult:
    """Fallback: check job by fetching its stored URL."""
    try:
        resp = await client.get(job.url)
    except httpx.TimeoutException:
        return JobCheckResult(job.job_id, CheckResult.ERROR, "timeout")
    except httpx.ConnectError as e:
        return JobCheckResult(job.job_id, CheckResult.ERROR, f"connect error: {e}")
    except httpx.HTTPError as e:
        return JobCheckResult(job.job_id, CheckResult.ERROR, f"http error: {e}")

    # Definitive 404 = inactive
    if resp.status_code == 404:
        return JobCheckResult(job.job_id, CheckResult.INACTIVE, "url 404")

    # Redirect — check if it goes to the board root (= job removed)
    if resp.status_code in (301, 302, 303, 307, 308):
        location = resp.headers.get("location", "")
        # If redirect target is shorter (board root) or different domain, likely removed
        if location and _is_board_root_redirect(job.url, location):
            return JobCheckResult(job.job_id, CheckResult.INACTIVE, f"redirect to board root: {location}")
        # Otherwise, try following the redirect
        try:
            resp2 = await client.get(location)
            if resp2.status_code == 404:
                return JobCheckResult(job.job_id, CheckResult.INACTIVE, "redirect target 404")
            body = resp2.text[:5000]
        except Exception:
            return JobCheckResult(job.job_id, CheckResult.ERROR, "redirect follow failed")
    elif resp.status_code >= 500:
        return JobCheckResult(job.job_id, CheckResult.ERROR, f"server error {resp.status_code}")
    elif resp.status_code == 200:
        body = resp.text[:5000]
    else:
        return JobCheckResult(job.job_id, CheckResult.ERROR, f"unexpected status {resp.status_code}")

    # Check body for "no longer available" patterns
    if _INACTIVE_RE.search(body):
        return JobCheckResult(job.job_id, CheckResult.INACTIVE, "inactive text detected")

    return JobCheckResult(job.job_id, CheckResult.OK, f"url {resp.status_code}")


def _is_board_root_redirect(original_url: str, redirect_url: str) -> bool:
    """Check if redirect target is a career board root (job removed pattern)."""
    orig = urlparse(original_url)
    redir = urlparse(redirect_url)
    # Same domain, but redirect path is a prefix of original (e.g. /jobs → /)
    if orig.netloc == redir.netloc or not redir.netloc:
        redir_path = redir.path.rstrip("/")
        orig_path = orig.path.rstrip("/")
        if len(redir_path) < len(orig_path):
            return True
    return False
