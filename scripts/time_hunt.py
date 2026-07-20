"""Time the full hunt flow on a random Crunchbase company at rank 4000–5000.

Reports:
  - source fetch time (Crunchbase API)
  - agent discover_company time (search + fingerprint + probe + LLM)
  - search calls, LLM calls
  - whether a YAML was written (the "PR" step in the local-write flow)
"""

import asyncio
import logging
import random
import sys
import time

from artemis.discovery.agent import discover_company
from artemis.discovery.sources import fetch_crunchbase_top

logging.basicConfig(
    level=logging.WARNING,  # quiet DDG/Azure noise; agent INFOs still appear
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logging.getLogger("artemis.discovery.agent").setLevel(logging.INFO)


async def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    rng = random.Random(seed)

    print(f"\n== Step 1: fetching Crunchbase ranks 1–5000 (seed={seed}) ==")
    t0 = time.perf_counter()
    pool = await fetch_crunchbase_top(limit=5000)
    fetch_s = time.perf_counter() - t0
    print(f"  fetched {len(pool)} companies in {fetch_s:.1f}s")

    # Slice ranks 4000–5000 (0-indexed 3999..)
    tail = pool[3999:]
    if not tail:
        print("ERROR: fewer than 4000 companies returned")
        return 2
    pick = rng.choice(tail)
    name = pick["name"]
    website = pick.get("website", "")
    print("\n== Step 2: picked random company ==")
    print(f"  name    : {name}")
    print(f"  website : {website}")

    print("\n== Step 3: hunt (discover_company) ==")
    t0 = time.perf_counter()
    result = await discover_company(name, website=website)
    hunt_s = time.perf_counter() - t0

    print("\n== Results ==")
    print(f"  status            : {result.status}")
    print(f"  ats               : {result.ats}")
    print(f"  ats_config        : {result.ats_config}")
    print(f"  evidence_url      : {result.evidence_url}")
    print(f"  discovered_jobs   : {result.discovered_jobs}")
    print(f"  search_calls      : {result.search_calls}")
    print(f"  llm_calls         : {result.llm_calls}")
    print(f"  est_cost_usd      : ~${result.llm_calls * 0.01:.4f}")
    print("\n== Timing ==")
    print(f"  crunchbase fetch  : {fetch_s:.1f}s")
    print(f"  hunt (end-to-end) : {hunt_s:.1f}s")
    yaml_written = result.status == "discovered"
    print(f"  YAML written      : {yaml_written}  ({'configs/companies/' + result.slug + '.yaml' if yaml_written else '-'})")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
