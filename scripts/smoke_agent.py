"""One-off smoke test for the discovery agent."""

import asyncio

from artemis.discovery.agent import discover_company


async def main():
    targets = [
        "Costco", "Walgreens", "Target", "Home Depot", "Kroger",
        "Delta Air Lines", "JPMorgan Chase", "Capital One", "American Airlines",
    ]
    for name in targets:
        r = await discover_company(name, dry_run=True)
        cfg = r.ats_config or {}
        slug = (
            cfg.get("board_token")
            or cfg.get("tenant")
            or cfg.get("site")
            or cfg.get("company")
            or cfg.get("careers_url")
            or "-"
        )
        print(
            f"{name:25} status={r.status:14} ats={str(r.ats):16} "
            f"slug={str(slug):30} jobs={r.discovered_jobs:5} "
            f"llm={r.llm_calls} search={r.search_calls} t={r.elapsed_sec:.1f}s"
        )
        if r.evidence_url:
            print(f"  evidence: {r.evidence_url}")


if __name__ == "__main__":
    asyncio.run(main())
