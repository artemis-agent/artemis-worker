"""
Fortune 500 Direct Scraper Test

Tests scrapers directly with known ATS configurations (bypasses detector).
This is the practical approach — we KNOW what ATS each company uses.
"""

import asyncio
import sys
import time
import json

from artemis.scrapers.registry import get_scraper


# Curated list: company -> ATS type + config (researched manually)
FORTUNE_500_ATS = [
    # ── Greenhouse ───────────────────────────────────────────
    {"name": "Cloudflare", "ats": "greenhouse", "config": {"board_token": "cloudflare"}},
    {"name": "Netflix", "ats": "greenhouse", "config": {"board_token": "netflix"}},
    {"name": "Palantir", "ats": "greenhouse", "config": {"board_token": "palantirtechnologies"}},
    {"name": "Nike", "ats": "greenhouse", "config": {"board_token": "nike"}},
    {"name": "Disney", "ats": "greenhouse", "config": {"board_token": "waltdisneycompany"}},
    {"name": "Stripe", "ats": "greenhouse", "config": {"board_token": "stripe"}},
    {"name": "Visa", "ats": "greenhouse", "config": {"board_token": "visa"}},
    {"name": "Mastercard", "ats": "greenhouse", "config": {"board_token": "mastercard"}},
    {"name": "Goldman Sachs", "ats": "greenhouse", "config": {"board_token": "goldmansachs"}},
    # ── Lever ────────────────────────────────────────────────
    {"name": "Netflix (Lever)", "ats": "lever", "config": {"company": "netflix"}},
    # ── Workday ──────────────────────────────────────────────
    {
        "name": "Salesforce",
        "ats": "workday",
        "config": {"tenant": "salesforce", "site_id": "External_Career_Site", "wd_version": "5"},
    },
    {
        "name": "Visa (Workday)",
        "ats": "workday",
        "config": {"tenant": "visa", "site_id": "External_Visa_Careers", "wd_version": "5"},
    },
    {"name": "Target", "ats": "workday", "config": {"tenant": "target", "site_id": "targetcareers", "wd_version": "5"}},
    {
        "name": "Adobe",
        "ats": "workday",
        "config": {"tenant": "adobe", "site_id": "External_Career_Site", "wd_version": "5"},
    },
    {
        "name": "Accenture",
        "ats": "workday",
        "config": {"tenant": "accenture", "site_id": "AccentureCareers", "wd_version": "5"},
    },
    {
        "name": "Bank of America",
        "ats": "workday",
        "config": {"tenant": "bankofamerica", "site_id": "Careers", "wd_version": "5"},
    },
    {
        "name": "JPMorgan Chase",
        "ats": "workday",
        "config": {"tenant": "jpmorgan", "site_id": "Careers", "wd_version": "5"},
    },
    {"name": "Deloitte", "ats": "workday", "config": {"tenant": "deloitte", "site_id": "Careers", "wd_version": "5"}},
    {
        "name": "Morgan Stanley",
        "ats": "workday",
        "config": {"tenant": "morganstanley", "site_id": "MS_External_Career_Site", "wd_version": "5"},
    },
    {
        "name": "FedEx",
        "ats": "workday",
        "config": {"tenant": "fedex", "site_id": "FXExternalCareerSite", "wd_version": "5"},
    },
    {
        "name": "Intel",
        "ats": "workday",
        "config": {"tenant": "intel", "site_id": "IntelExternalCareerSite", "wd_version": "1"},
    },
    {
        "name": "Johnson & Johnson",
        "ats": "workday",
        "config": {"tenant": "jnjfamily", "site_id": "Careers", "wd_version": "5"},
    },
    {"name": "Pfizer", "ats": "workday", "config": {"tenant": "pfizer", "site_id": "Careers", "wd_version": "5"}},
    {
        "name": "Merck",
        "ats": "workday",
        "config": {"tenant": "merck", "site_id": "ExternalCareerSite", "wd_version": "5"},
    },
    {
        "name": "ExxonMobil",
        "ats": "workday",
        "config": {"tenant": "exxonmobil", "site_id": "Careers", "wd_version": "5"},
    },
    {
        "name": "Chevron",
        "ats": "workday",
        "config": {"tenant": "chevron", "site_id": "ExternalCareerSite", "wd_version": "5"},
    },
    {
        "name": "Boeing",
        "ats": "workday",
        "config": {"tenant": "boeing", "site_id": "BoeingExternalSite", "wd_version": "5"},
    },
    {
        "name": "Lockheed Martin",
        "ats": "workday",
        "config": {"tenant": "lockheedmartin", "site_id": "ExternalSite", "wd_version": "5"},
    },
    {
        "name": "Raytheon (RTX)",
        "ats": "workday",
        "config": {"tenant": "rtx", "site_id": "ExternalSite", "wd_version": "5"},
    },
    {
        "name": "General Electric",
        "ats": "workday",
        "config": {"tenant": "ge", "site_id": "GEExternalSite", "wd_version": "5"},
    },
    {
        "name": "Walmart",
        "ats": "workday",
        "config": {"tenant": "walmart", "site_id": "ExternalSite", "wd_version": "5"},
    },
    {"name": "UPS", "ats": "workday", "config": {"tenant": "ups", "site_id": "UPSExternalSite", "wd_version": "5"}},
    {
        "name": "Verizon",
        "ats": "workday",
        "config": {"tenant": "verizon", "site_id": "ExternalSite", "wd_version": "5"},
    },
    {"name": "AT&T", "ats": "workday", "config": {"tenant": "att", "site_id": "ExternalSite", "wd_version": "5"}},
    {
        "name": "T-Mobile",
        "ats": "workday",
        "config": {"tenant": "tmobile", "site_id": "ExternalSite", "wd_version": "5"},
    },
    {"name": "Costco", "ats": "workday", "config": {"tenant": "costco", "site_id": "ExternalSite", "wd_version": "5"}},
    {
        "name": "Eli Lilly",
        "ats": "workday",
        "config": {"tenant": "lilly", "site_id": "ExternalSite", "wd_version": "5"},
    },
    {
        "name": "ConocoPhillips",
        "ats": "workday",
        "config": {"tenant": "conocophillips", "site_id": "ExternalSite", "wd_version": "5"},
    },
    {
        "name": "UnitedHealth Group",
        "ats": "workday",
        "config": {"tenant": "unitedhealthgroup", "site_id": "ExternalSite", "wd_version": "5"},
    },
    {
        "name": "Procter & Gamble",
        "ats": "workday",
        "config": {"tenant": "pg", "site_id": "ExternalSite", "wd_version": "5"},
    },
    # ── Ashby ────────────────────────────────────────────────
    {"name": "Snowflake", "ats": "ashby", "config": {"board_token": "snowflake"}},
    # ── Eightfold ────────────────────────────────────────────
    {"name": "Nvidia", "ats": "eightfold", "config": {"company": "nvidia", "domain": "nvidia.com"}},
    # ── SmartRecruiters ──────────────────────────────────────
    {"name": "Cisco", "ats": "smartrecruiters", "config": {"company_id": "CiscoSystems"}},
    {"name": "Accenture (SR)", "ats": "smartrecruiters", "config": {"company_id": "Accenture"}},
    # ── Custom (needs dedicated scraper) ─────────────────────
    # These are noted for future implementation
    {
        "name": "Apple",
        "ats": "custom",
        "config": {"careers_url": "https://jobs.apple.com/en-us/search"},
        "note": "Custom SPA, Apple-proprietary API",
    },
    {
        "name": "Amazon",
        "ats": "custom",
        "config": {"careers_url": "https://amazon.jobs"},
        "note": "Custom portal with CSRF",
    },
    {
        "name": "Google",
        "ats": "custom",
        "config": {"careers_url": "https://careers.google.com/jobs"},
        "note": "Custom React SPA",
    },
    {
        "name": "Meta",
        "ats": "custom",
        "config": {"careers_url": "https://www.metacareers.com/jobs"},
        "note": "Custom React SPA",
    },
    {
        "name": "Tesla",
        "ats": "custom",
        "config": {"careers_url": "https://www.tesla.com/careers/search"},
        "note": "Custom JS SPA",
    },
    {
        "name": "Microsoft",
        "ats": "custom",
        "config": {"careers_url": "https://careers.microsoft.com/us/en/search-results"},
        "note": "Custom SPA",
    },
    {
        "name": "Oracle",
        "ats": "custom",
        "config": {"careers_url": "https://careers.oracle.com/jobs"},
        "note": "Custom Taleo/Oracle Cloud HCM",
    },
    {"name": "IBM", "ats": "custom", "config": {"careers_url": "https://ibm.com/careers/search"}, "note": "Custom SPA"},
]


async def test_scraper(entry: dict) -> dict:
    name = entry["name"]
    ats = entry["ats"]
    config = entry["config"]
    result = {"name": name, "ats": ats, "jobs_found": 0, "error": None, "note": entry.get("note")}

    if ats == "custom":
        result["error"] = "needs_custom_scraper"
        return result

    try:
        scraper = get_scraper(ats, config)
        async with scraper:
            jobs = await scraper.scrape(query="", limit=10)
        result["jobs_found"] = len(jobs)
        if jobs:
            result["sample_title"] = jobs[0].title
        if not jobs:
            result["error"] = "0_jobs_returned"
    except Exception as e:
        result["error"] = str(e)[:100]

    return result


async def main():
    companies = FORTUNE_500_ATS
    print(f"Testing {len(companies)} Fortune 500 companies directly...\n")

    results = []
    for i, entry in enumerate(companies):
        sys.stdout.write(f"[{i + 1}/{len(companies)}] {entry['name']:30s} ({entry['ats']:15s})... ")
        sys.stdout.flush()
        start = time.time()
        try:
            r = await asyncio.wait_for(test_scraper(entry), timeout=45)
        except asyncio.TimeoutError:
            r = {"name": entry["name"], "ats": entry["ats"], "jobs_found": 0, "error": "timeout (45s)"}
        elapsed = time.time() - start
        results.append(r)

        if r["jobs_found"] > 0:
            print(f"OK  jobs={r['jobs_found']:3d} ({elapsed:.1f}s) sample: {r.get('sample_title', '')[:50]}")
        elif r.get("note"):
            print(f"SKIP ({r['note'][:40]})")
        else:
            print(f"FAIL ({elapsed:.1f}s) error={r.get('error', '?')[:60]}")

    # Summary
    print("\n" + "=" * 90)
    success = [r for r in results if r["jobs_found"] > 0]
    failed = [r for r in results if r["jobs_found"] == 0 and r.get("error") != "needs_custom_scraper"]
    custom = [r for r in results if r.get("error") == "needs_custom_scraper"]

    print(f"\n✅ WORKING ({len(success)}/{len(companies)}):")
    for r in sorted(success, key=lambda x: -x["jobs_found"]):
        print(f"  {r['name']:30s} {r['ats']:15s} jobs={r['jobs_found']}")

    print(f"\n❌ FAILED ({len(failed)}):")
    for r in failed:
        print(f"  {r['name']:30s} {r['ats']:15s} error={r.get('error', '?')}")

    print(f"\n🔧 NEEDS CUSTOM SCRAPER ({len(custom)}):")
    for r in custom:
        print(f"  {r['name']:30s} {r.get('note', '')}")

    # Save
    with open("/tmp/fortune500_scrape_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("\nFull results saved to /tmp/fortune500_scrape_results.json")


if __name__ == "__main__":
    asyncio.run(main())
