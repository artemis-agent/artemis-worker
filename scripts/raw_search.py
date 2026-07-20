"""Debug: run a raw DDG query."""

import asyncio
import sys

from artemis.discovery.agent import _extract_candidates
from artemis.discovery.search import default_searcher


async def main():
    q = sys.argv[1] if len(sys.argv) > 1 else "Target careers myworkdayjobs"
    searcher = default_searcher()
    results = await searcher.search(q, max_results=10)
    print(f"\n== Raw query: {q!r} ==")
    for i, r in enumerate(results, 1):
        print(f"{i:>2}. {r.url}")
        print(f"    {r.title[:90]}")
    cands = _extract_candidates(results)
    print(f"\n== Extracted: {len(cands)} ==")
    for c in cands:
        print(f"  {c.ats}: {c.config}")


if __name__ == "__main__":
    asyncio.run(main())
