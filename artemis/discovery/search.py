"""Web-search backend used by the discovery agent.

DuckDuckGo via the free `ddgs` package — no API key, no infrastructure.
DDG soft-limits ~30 q/min from a single IP; the daily-cap (30/day)
discovery loop fits comfortably under that. Bulk runs may hit
rate-limits; that's a known tradeoff for staying free.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Protocol


logger = logging.getLogger("artemis.discovery.search")


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


class WebSearch(Protocol):
    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]: ...


class DuckDuckGoSearcher:
    """Async wrapper around the synchronous `ddgs` package.

    `DDGS().text()` is blocking, so we run it in a thread to keep the
    discovery agent fully async.
    """

    def __init__(self, region: str = "wt-wt", safesearch: str = "off"):
        self._region = region
        self._safesearch = safesearch

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        return await asyncio.to_thread(self._search_sync, query, max_results)

    def _search_sync(self, query: str, max_results: int) -> list[SearchResult]:
        try:
            from ddgs import DDGS
        except ImportError as e:
            raise RuntimeError("ddgs package not installed. `pip install ddgs`.") from e

        out: list[SearchResult] = []
        try:
            with DDGS() as ddgs:
                for row in ddgs.text(
                    query=query,
                    region=self._region,
                    safesearch=self._safesearch,
                    max_results=max_results,
                ):
                    out.append(
                        SearchResult(
                            title=row.get("title", "") or "",
                            url=row.get("href", "") or row.get("url", "") or "",
                            snippet=row.get("body", "") or "",
                        )
                    )
        except Exception as e:
            logger.warning(f"DDG search failed for {query!r}: {e}")
        return out


_default: WebSearch | None = None


def default_searcher() -> WebSearch:
    global _default
    if _default is None:
        _default = DuckDuckGoSearcher()
    return _default
