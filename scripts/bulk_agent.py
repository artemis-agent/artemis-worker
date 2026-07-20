"""One-off bulk agent discovery — no Celery, no time limit."""

import asyncio
import logging
import sys

from artemis.discovery.bulk import (
    bulk_discover_via_agent,
    _candidates_not_yet_known,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


async def main():
    max_companies = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
    concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    names = _candidates_not_yet_known(max_companies)
    print("\n== Bulk agent discovery ==")
    print(f"  candidates : {len(names)}")
    print(f"  concurrency: {concurrency}")
    print(f"  estimated  : ~{len(names) * 10 / concurrency / 60:.0f} min")
    print()

    result = await bulk_discover_via_agent(
        names,
        concurrency=concurrency,
        max_companies=max_companies,
        summary_path="/tmp/agent_bulk_summary.json",
    )

    print(f"\n== DONE in {result['elapsed_sec']}s ==")
    print(f"  hits           : {result['hits']}")
    print(f"  not_found      : {result['not_found']}")
    print(f"  errors         : {result['errors']}")
    print(f"  total_llm_calls: {result['total_llm_calls']}")
    print(f"  est_cost_usd   : ${result['est_cost_usd']}")
    print(f"  by_ats         : {result['by_ats']}")


if __name__ == "__main__":
    asyncio.run(main())
