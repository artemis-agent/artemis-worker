"""End-to-end demo of the Crunchbase-anchored discovery flow.

Pipeline:
    crunchbase permalink
        -> fetch_crunchbase_website()       (Crunchbase API)
        -> discover_company(website=...)    (domain-anchored DDG queries)
        -> ATS candidates -> probe -> verify
"""
from __future__ import annotations

import asyncio
import logging
import sys

from artemis.discovery.agent import discover_company, _query_domain
from artemis.discovery.search import DuckDuckGoSearcher
from artemis.discovery.sources import fetch_crunchbase_website


class _SearchSpy(DuckDuckGoSearcher):
    """Logs every search query that gets issued."""
    async def search(self, query, max_results=10):
        print(f"  [search] q={query!r}  (max={max_results})")
        return await super().search(query, max_results=max_results)


async def demo(permalink: str):
    print(f"\n{'='*70}\nCRUNCHBASE PERMALINK: {permalink}\n{'='*70}")

    print("\n[1] Resolve permalink -> website via Crunchbase API")
    website = await fetch_crunchbase_website(permalink)
    print(f"    website = {website}")
    if not website:
        print("    (cannot continue without a website)")
        return

    print(f"\n[2] Domain extracted for search anchoring")
    print(f"    domain  = {_query_domain(website)}")

    print(f"\n[3] Running discover_company (dry_run=True, no YAML written)")
    print(f"    queries that will be issued:")
    company_name = permalink.replace("-", " ").title()
    result = await discover_company(
        name=company_name,
        website=website,
        searcher=_SearchSpy(),
        dry_run=True,
    )

    print(f"\n[4] Result")
    print(f"    status         = {result.status}")
    print(f"    ats            = {result.ats}")
    print(f"    ats_config     = {result.ats_config}")
    print(f"    careers_url    = {result.careers_url}")
    print(f"    evidence_url   = {result.evidence_url}")
    print(f"    discovered_jobs= {result.discovered_jobs}")
    print(f"    search_calls   = {result.search_calls}")
    print(f"    llm_calls      = {result.llm_calls}")
    print(f"    elapsed_sec    = {result.elapsed_sec:.2f}")


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="    [%(name)s] %(message)s",
        stream=sys.stdout,
    )
    # Quiet down noisy httpx/asyncio loggers; keep our discovery logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    for permalink in sys.argv[1:] or ["hashicorp"]:
        await demo(permalink)


if __name__ == "__main__":
    asyncio.run(main())
