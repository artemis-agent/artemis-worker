import pathlib
from typing import Optional

import yaml
from pydantic import BaseModel

from artemis.core.config import settings
from artemis.core.models import ATSType, CompanyStatus


class CompanyConfig(BaseModel):
    name: str
    slug: str
    ats: ATSType
    careers_url: str
    ats_config: dict = {}
    verified: bool = False
    last_verified: Optional[str] = None


def load_company_configs(configs_dir: str | None = None) -> list[CompanyConfig]:
    base = pathlib.Path(configs_dir or settings.configs_dir)
    if not base.exists():
        return []

    configs = []
    for path in sorted(base.glob("*.yaml")):
        with open(path) as f:
            data = yaml.safe_load(f)
        configs.append(CompanyConfig(**data))
    return configs


async def sync_configs_to_db(configs_dir: str | None = None):
    from sqlalchemy import select
    from artemis.core.database import async_session
    from artemis.core.models import Company

    configs = load_company_configs(configs_dir)
    async with async_session() as session:
        for cfg in configs:
            result = await session.execute(select(Company).where(Company.slug == cfg.slug))
            existing = result.scalar_one_or_none()

            if existing:
                existing.name = cfg.name
                existing.ats_type = cfg.ats
                existing.careers_url = cfg.careers_url
                existing.ats_config = cfg.ats_config
                existing.status = CompanyStatus.active if cfg.verified else CompanyStatus.pending
            else:
                company = Company(
                    name=cfg.name,
                    slug=cfg.slug,
                    ats_type=cfg.ats,
                    careers_url=cfg.careers_url,
                    ats_config=cfg.ats_config,
                    status=CompanyStatus.active if cfg.verified else CompanyStatus.pending,
                )
                session.add(company)

        await session.commit()

    return len(configs)
