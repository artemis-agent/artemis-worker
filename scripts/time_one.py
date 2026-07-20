"""Time a hunt on a specific company name (for known-good demos)."""

import asyncio
import logging
import sys
import time

from artemis.discovery.agent import discover_company

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("artemis.discovery.agent").setLevel(logging.INFO)


async def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "Vanta"
    # Clear any existing yaml so the early-exit doesn't short-circuit.
    import pathlib, re
    from artemis.core.config import settings
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    p = pathlib.Path(settings.configs_dir) / f"{slug}.yaml"
    if p.exists():
        p.unlink()
        print(f"removed existing {p}")

    print(f"\n== hunt: {name!r} ==")
    t0 = time.perf_counter()
    r = await discover_company(name)
    dt = time.perf_counter() - t0

    print(f"\n  status            : {r.status}")
    print(f"  ats               : {r.ats}")
    print(f"  ats_config        : {r.ats_config}")
    print(f"  discovered_jobs   : {r.discovered_jobs}")
    print(f"  evidence_url      : {r.evidence_url}")
    print(f"  search_calls      : {r.search_calls}")
    print(f"  llm_calls         : {r.llm_calls}")
    print(f"  est_cost_usd      : ~${r.llm_calls * 0.01:.4f}")
    print(f"  total elapsed     : {dt:.1f}s")
    print(f"  YAML written      : {p.exists()}  ({p if p.exists() else '-'})")


if __name__ == "__main__":
    asyncio.run(main())
