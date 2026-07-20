"""Debug: show search results + extracted candidates for one company."""

import asyncio
import sys

from artemis.discovery.agent import _extract_candidates
from artemis.discovery.search import default_searcher


async def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "Eli Lilly"
    searcher = default_searcher()
    results = await searcher.search(f'"{name}" careers', max_results=10)
    print(f"\n== Search results for {name!r} ==")
    for i, r in enumerate(results, 1):
        print(f"{i:>2}. {r.url}")
        print(f"    {r.title[:100]}")
    cands = _extract_candidates(results)
    print(f"\n== Extracted candidates: {len(cands)} ==")
    for c in cands:
        print(f"  ats={c.ats:<16} slug={c.slug:<25} cfg={c.config}")
        print(f"    via {c.evidence_url}")


if __name__ == "__main__":
    asyncio.run(main())
