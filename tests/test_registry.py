import pytest
from artemis.scrapers.registry import get_scraper, list_scrapers
from artemis.core.models import ATSType
from artemis.scrapers.base import BaseScraper


class TestRegistry:
    def test_all_ats_types_registered(self):
        registered = list_scrapers()
        expected = {
            ATSType.greenhouse, ATSType.lever, ATSType.ashby,
            ATSType.workday, ATSType.eightfold, ATSType.icims,
            ATSType.smartrecruiters, ATSType.custom,
        }
        assert expected.issubset(set(registered.keys()))

    def test_get_scraper_returns_base_scraper(self):
        scraper = get_scraper("greenhouse", {"board_token": "test"})
        assert isinstance(scraper, BaseScraper)

    def test_get_scraper_passes_config(self):
        scraper = get_scraper("ashby", {"board_token": "xyz"})
        assert scraper.ats_config["board_token"] == "xyz"

    def test_invalid_ats_type_raises(self):
        with pytest.raises(ValueError):
            get_scraper("does_not_exist", {})
