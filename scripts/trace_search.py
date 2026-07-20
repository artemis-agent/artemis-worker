"""Trace what the composite searcher actually returns."""

import asyncio
import logging

from artemis.discovery.search import default_searcher

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


async def main():
    s = default_searcher()
    print(f"searcher type: {type(s).__name__}")
    for q in ["Benepass careers", "Stripe careers", "Vanta jobs"]:
        r = await s.search(q, max_results=5)
        print(f"\n{q!r}: {len(r)} results")
        for x in r[:3]:
            print(f"  {x.url[:80]}")
            print(f"    {(x.title or '')[:80]}")


if __name__ == "__main__":
    asyncio.run(main())
