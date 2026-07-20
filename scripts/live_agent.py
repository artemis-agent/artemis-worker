"""Live discovery — actually writes YAMLs."""

import asyncio
import sys

from artemis.discovery.agent import discover_company


async def main():
    names = sys.argv[1:] or [
        "Target", "Costco", "Walgreens", "JPMorgan Chase",
        "Home Depot", "Delta Air Lines", "Capital One",
    ]
    for name in names:
        r = await discover_company(name, dry_run=False)
        cfg = r.ats_config or {}
        slug = (
            cfg.get("board_token")
            or cfg.get("tenant")
            or cfg.get("site")
            or cfg.get("company")
            or "-"
        )
        print(
            f"{name:25} {r.status:14} ats={str(r.ats):16} "
            f"slug={str(slug):25} jobs={r.discovered_jobs:5} "
            f"llm={r.llm_calls} search={r.search_calls} t={r.elapsed_sec:.1f}s"
        )
        if r.evidence_url:
            print(f"  evidence: {r.evidence_url}")


if __name__ == "__main__":
    asyncio.run(main())
