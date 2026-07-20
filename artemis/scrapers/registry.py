from artemis.core.models import ATSType
from artemis.scrapers.base import BaseScraper


_REGISTRY: dict[ATSType, type[BaseScraper]] = {}


def register(ats_type: ATSType):
    def decorator(cls: type[BaseScraper]):
        cls.ats_type = ats_type
        _REGISTRY[ats_type] = cls
        return cls

    return decorator


def get_scraper(ats_type: ATSType | str, ats_config: dict | None = None) -> BaseScraper:
    if isinstance(ats_type, str):
        ats_type = ATSType(ats_type)

    cls = _REGISTRY.get(ats_type)
    if cls is None:
        raise ValueError(f"No scraper registered for ATS type: {ats_type}")
    return cls(ats_config=ats_config)


def list_scrapers() -> dict[ATSType, type[BaseScraper]]:
    return dict(_REGISTRY)


# Import all scraper modules to trigger registration
def _load_all():
    from artemis.scrapers.ats import greenhouse, lever, ashby, workday, eightfold, icims, smartrecruiters, generic  # noqa: F401


_load_all()
