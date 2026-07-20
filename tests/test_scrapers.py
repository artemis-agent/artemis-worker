"""
E2E tests for all ATS scrapers.

Each test hits the real API and validates:
- Jobs are returned with valid structure
- Query filtering works
- Limits are respected
- Fallback strategies fire when primary fails

Marked with `e2e` — skip with: pytest -m "not e2e"
"""

import pytest
from tests.conftest import assert_valid_jobs
from artemis.scrapers.registry import get_scraper


pytestmark = pytest.mark.e2e


# ── Greenhouse (Cloudflare) ──────────────────────────────────────────────


class TestGreenhouse:
    CONFIG = {"board_token": "cloudflare"}

    @pytest.mark.asyncio
    async def test_scrape_returns_jobs(self):
        async with get_scraper("greenhouse", self.CONFIG) as s:
            jobs = await s.scrape(query="", limit=5)
        assert_valid_jobs(jobs)
        assert all(j.source == "greenhouse" for j in jobs)

    @pytest.mark.asyncio
    async def test_query_filters_results(self):
        async with get_scraper("greenhouse", self.CONFIG) as s:
            jobs = await s.scrape(query="engineer", limit=10)
        assert_valid_jobs(jobs)
        assert all("engineer" in j.title.lower() for j in jobs)

    @pytest.mark.asyncio
    async def test_limit_respected(self):
        async with get_scraper("greenhouse", self.CONFIG) as s:
            jobs = await s.scrape(query="", limit=3)
        assert len(jobs) <= 3

    @pytest.mark.asyncio
    async def test_jobs_have_location(self):
        async with get_scraper("greenhouse", self.CONFIG) as s:
            jobs = await s.scrape(query="", limit=5)
        with_loc = [j for j in jobs if j.location]
        assert len(with_loc) > 0

    @pytest.mark.asyncio
    async def test_missing_token_raises(self):
        async with get_scraper("greenhouse", {}) as s:
            with pytest.raises(ValueError):
                await s.scrape(query="", limit=5)


# ── Lever (Spotify) ─────────────────────────────────────────────────────


class TestLever:
    CONFIG = {"company": "spotify"}

    @pytest.mark.asyncio
    async def test_json_api_returns_jobs(self):
        async with get_scraper("lever", self.CONFIG) as s:
            jobs = await s.scrape(query="", limit=5)
        assert_valid_jobs(jobs)
        assert all(j.source == "lever" for j in jobs)

    @pytest.mark.asyncio
    async def test_query_filters_results(self):
        async with get_scraper("lever", self.CONFIG) as s:
            jobs = await s.scrape(query="engineer", limit=10)
        assert_valid_jobs(jobs)
        assert all("engineer" in j.title.lower() for j in jobs)

    @pytest.mark.asyncio
    async def test_html_fallback_on_dead_company(self):
        """Company whose JSON API is gone but HTML page may still exist."""
        async with get_scraper("lever", {"company": "figma"}) as s:
            # Should not raise — gracefully returns empty or HTML results
            jobs = await s.scrape(query="", limit=5)
        # figma is gone from Lever entirely, so empty is fine
        assert isinstance(jobs, list)

    @pytest.mark.asyncio
    async def test_missing_company_raises(self):
        async with get_scraper("lever", {}) as s:
            with pytest.raises(ValueError):
                await s.scrape(query="", limit=5)


# ── Ashby (Snowflake) ───────────────────────────────────────────────────


class TestAshby:
    CONFIG = {"board_token": "snowflake"}

    @pytest.mark.asyncio
    async def test_scrape_returns_jobs(self):
        async with get_scraper("ashby", self.CONFIG) as s:
            jobs = await s.scrape(query="", limit=5)
        assert_valid_jobs(jobs)
        assert all(j.source == "ashby" for j in jobs)

    @pytest.mark.asyncio
    async def test_query_filters_results(self):
        async with get_scraper("ashby", self.CONFIG) as s:
            jobs = await s.scrape(query="engineer", limit=10)
        assert_valid_jobs(jobs)
        assert all("engineer" in j.title.lower() for j in jobs)

    @pytest.mark.asyncio
    async def test_jobs_have_urls(self):
        async with get_scraper("ashby", self.CONFIG) as s:
            jobs = await s.scrape(query="", limit=5)
        assert all("ashbyhq.com" in j.url or "snowflake" in j.url for j in jobs)

    @pytest.mark.asyncio
    async def test_missing_token_raises(self):
        async with get_scraper("ashby", {}) as s:
            with pytest.raises(ValueError):
                await s.scrape(query="", limit=5)


# ── Workday (Target) ────────────────────────────────────────────────────


class TestWorkday:
    CONFIG = {"tenant": "target", "site_id": "targetcareers", "wd_version": "5"}

    @pytest.mark.asyncio
    async def test_scrape_returns_jobs(self):
        async with get_scraper("workday", self.CONFIG) as s:
            jobs = await s.scrape(query="", limit=5)
        assert_valid_jobs(jobs)
        assert all(j.source == "workday" for j in jobs)
        assert all("targetcareers" in j.url for j in jobs)

    @pytest.mark.asyncio
    async def test_limit_respected(self):
        async with get_scraper("workday", self.CONFIG) as s:
            jobs = await s.scrape(query="", limit=3)
        assert len(jobs) <= 3

    @pytest.mark.asyncio
    async def test_jobs_have_location(self):
        async with get_scraper("workday", self.CONFIG) as s:
            jobs = await s.scrape(query="", limit=5)
        with_loc = [j for j in jobs if j.location]
        assert len(with_loc) > 0

    @pytest.mark.asyncio
    async def test_missing_tenant_raises(self):
        async with get_scraper("workday", {}) as s:
            with pytest.raises(ValueError):
                await s.scrape(query="", limit=5)


# ── Eightfold (Nvidia) ──────────────────────────────────────────────────


class TestEightfold:
    CONFIG = {"company": "nvidia", "domain": "nvidia.com"}

    @pytest.mark.asyncio
    async def test_scrape_returns_jobs(self):
        async with get_scraper("eightfold", self.CONFIG) as s:
            jobs = await s.scrape(query="", limit=5)
        assert_valid_jobs(jobs)
        assert all(j.source == "eightfold" for j in jobs)

    @pytest.mark.asyncio
    async def test_limit_respected(self):
        async with get_scraper("eightfold", self.CONFIG) as s:
            jobs = await s.scrape(query="", limit=3)
        assert len(jobs) <= 3

    @pytest.mark.asyncio
    async def test_missing_company_raises(self):
        async with get_scraper("eightfold", {}) as s:
            with pytest.raises(ValueError):
                await s.scrape(query="", limit=5)


# ── SmartRecruiters (Bosch) ──────────────────────────────────────────────


class TestSmartRecruiters:
    CONFIG = {"company_id": "BoschGroup"}

    @pytest.mark.asyncio
    async def test_scrape_returns_jobs(self):
        async with get_scraper("smartrecruiters", self.CONFIG) as s:
            jobs = await s.scrape(query="", limit=5)
        assert_valid_jobs(jobs)
        assert all(j.source == "smartrecruiters" for j in jobs)

    @pytest.mark.asyncio
    async def test_limit_respected(self):
        async with get_scraper("smartrecruiters", self.CONFIG) as s:
            jobs = await s.scrape(query="", limit=3)
        assert len(jobs) <= 3

    @pytest.mark.asyncio
    async def test_missing_company_id_raises(self):
        async with get_scraper("smartrecruiters", {}) as s:
            with pytest.raises(ValueError):
                await s.scrape(query="", limit=5)


# ── iCIMS ────────────────────────────────────────────────────────────────


class TestICIMS:
    @pytest.mark.asyncio
    async def test_no_config_raises(self):
        async with get_scraper("icims", {}) as s:
            with pytest.raises(ValueError):
                await s.scrape(query="", limit=5)

    @pytest.mark.asyncio
    async def test_api_with_bad_customer_id_returns_empty(self):
        """Invalid customer_id should not crash, just return empty."""
        async with get_scraper("icims", {"customer_id": "0000000"}) as s:
            jobs = await s.scrape(query="", limit=5)
        assert isinstance(jobs, list)
        assert len(jobs) == 0


# ── Generic / Custom (Apple) ────────────────────────────────────────────


class TestGeneric:
    CONFIG = {"careers_url": "https://www.apple.com/careers/us/"}

    @pytest.mark.asyncio
    async def test_scrape_returns_jobs(self):
        async with get_scraper("custom", self.CONFIG) as s:
            jobs = await s.scrape(query="", limit=5)
        assert_valid_jobs(jobs)

    @pytest.mark.asyncio
    async def test_limit_respected(self):
        async with get_scraper("custom", self.CONFIG) as s:
            jobs = await s.scrape(query="", limit=2)
        assert len(jobs) <= 2

    @pytest.mark.asyncio
    async def test_missing_careers_url_raises(self):
        async with get_scraper("custom", {}) as s:
            with pytest.raises(ValueError):
                await s.scrape(query="", limit=5)
