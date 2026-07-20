"""
Fortune 500 ATS Detection & Scrape Test

Detects ATS type for each company, then scrapes jobs.
Outputs a report of successes, failures, and companies needing custom scrapers.
"""

import asyncio
import json
import sys
import time

from artemis.discovery.detector import detect_ats
from artemis.discovery.sources import FORTUNE_500_COMPANIES
from artemis.scrapers.registry import get_scraper


async def test_company(company: dict) -> dict:
    name = company["name"]
    hint = company["careers_hint"]
    url = f"https://{hint}" if not hint.startswith("http") else hint

    result = {"name": name, "careers_url": url, "ats_type": None, "confidence": 0, "jobs_found": 0, "error": None, "needs_custom": False}

    # Step 1: Detect ATS
    try:
        detection = await detect_ats(url)
        result["ats_type"] = detection.ats_type
        result["confidence"] = detection.confidence
        result["config"] = detection.config
    except Exception as e:
        result["error"] = f"detection_failed: {e}"
        result["needs_custom"] = True
        return result

    # Step 2: Try scraping if we detected an ATS
    if result["ats_type"] and result["ats_type"] != "unknown" and result["confidence"] >= 0.5:
        try:
            config = result.get("config", {})
            scraper = get_scraper(result["ats_type"], config)
            async with scraper:
                jobs = await scraper.scrape(query="", limit=10)
            result["jobs_found"] = len(jobs)
            if result["jobs_found"] == 0:
                result["error"] = "scrape_returned_0_jobs"
        except Exception as e:
            result["error"] = f"scrape_failed: {e}"
    else:
        result["needs_custom"] = True
        if not result["error"]:
            result["error"] = f"low_confidence_or_unknown (ats={result['ats_type']}, conf={result['confidence']:.2f})"

    return result


async def main():
    companies = FORTUNE_500_COMPANIES
    print(f"Testing {len(companies)} Fortune 500 companies...\n")

    results = []
    for i, company in enumerate(companies):
        sys.stdout.write(f"[{i+1}/{len(companies)}] {company['name']}... ")
        sys.stdout.flush()
        start = time.time()
        try:
            r = await asyncio.wait_for(test_company(company), timeout=30)
        except asyncio.TimeoutError:
            r = {"name": company["name"], "careers_url": f"https://{company['careers_hint']}", "ats_type": None, "confidence": 0, "jobs_found": 0, "error": "timeout", "needs_custom": True}
        elapsed = time.time() - start
        results.append(r)

        status = "OK" if r["jobs_found"] > 0 else "FAIL"
        ats = r.get("ats_type", "?") or "?"
        print(f"{status} | ATS={ats} conf={r.get('confidence', 0):.2f} jobs={r['jobs_found']} ({elapsed:.1f}s)")

    # Print summary
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)

    success = [r for r in results if r["jobs_found"] > 0]
    failed = [r for r in results if r["jobs_found"] == 0 and not r.get("needs_custom")]
    custom = [r for r in results if r.get("needs_custom")]

    print(f"\n✅ SUCCESS ({len(success)} companies):")
    for r in success:
        print(f"  {r['name']:30s} ATS={r['ats_type']:20s} jobs={r['jobs_found']}")

    print(f"\n❌ FAILED ({len(failed)} companies - ATS detected but scrape failed):")
    for r in failed:
        print(f"  {r['name']:30s} ATS={r.get('ats_type', '?'):20s} error={r.get('error', '?')}")

    print(f"\n🔧 NEEDS CUSTOM SCRAPER ({len(custom)} companies):")
    for r in custom:
        print(f"  {r['name']:30s} URL={r['careers_url']}")
        print(f"    {'':30s} reason={r.get('error', 'unknown/custom ATS')}")

    # Dump full results as JSON
    with open("/tmp/fortune500_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nFull results saved to /tmp/fortune500_results.json")


if __name__ == "__main__":
    asyncio.run(main())
