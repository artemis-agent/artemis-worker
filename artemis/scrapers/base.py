import asyncio
import random
from abc import ABC, abstractmethod
from datetime import datetime

import httpx

from artemis.core.models import ATSType

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
]


class ScrapedJob:
    __slots__ = ("external_id", "title", "url", "location", "description", "date_posted", "source", "metadata")

    def __init__(
        self,
        external_id: str,
        title: str,
        url: str,
        location: str | None = None,
        description: str | None = None,
        date_posted: datetime | None = None,
        source: str = "",
        metadata: dict | None = None,
    ):
        self.external_id = external_id
        self.title = title
        self.url = url
        self.location = location
        self.description = description
        self.date_posted = date_posted
        self.source = source
        self.metadata = metadata or {}


class BaseScraper(ABC):
    ats_type: ATSType

    def __init__(self, ats_config: dict | None = None, rate_limit: float = 1.5):
        self.ats_config = ats_config or {}
        self.rate_limit = rate_limit
        self._last_request_time = 0.0
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": random.choice(USER_AGENTS)},
                timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0),
                follow_redirects=True,
            )
        return self._client

    async def _throttle(self):
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    async def _get(self, url: str, **kwargs) -> httpx.Response:
        await self._throttle()
        client = await self._get_client()
        response = await client.get(url, **kwargs)
        response.raise_for_status()
        return response

    async def _post(self, url: str, **kwargs) -> httpx.Response:
        await self._throttle()
        client = await self._get_client()
        response = await client.post(url, **kwargs)
        response.raise_for_status()
        return response

    @abstractmethod
    async def scrape(
        self,
        query: str,
        limit: int = 50,
        skip_detail_urls: set[str] | None = None,
    ) -> list[ScrapedJob]: ...

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
