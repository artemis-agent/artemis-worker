from artemis.scrapers.base import ScrapedJob


def assert_valid_jobs(jobs: list[ScrapedJob], min_count: int = 1):
    """Common assertions for any scraper result."""
    assert len(jobs) >= min_count, f"Expected at least {min_count} jobs, got {len(jobs)}"
    for job in jobs:
        assert job.title, "Job title must not be empty"
        assert job.url, "Job URL must not be empty"
        assert job.url.startswith("http"), f"Job URL must be absolute: {job.url}"
        assert job.external_id, "Job external_id must not be empty"
        assert job.source, "Job source must not be empty"
