import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from artemis.core.models import ATSType
from artemis.scrapers.base import USER_AGENTS


@dataclass
class DetectionResult:
    ats_type: str  # ATSType value or "unknown"
    confidence: float  # 0.0 - 1.0
    config: dict = field(default_factory=dict)
    sample_jobs: int = 0
    details: str = ""


# ── URL patterns → ATS type + config extractor ──────────────────────────

_URL_PATTERNS: list[tuple[re.Pattern, str, callable]] = [
    (re.compile(r"boards\.greenhouse\.io/(\w+)", re.I), "greenhouse", lambda m: {"board_token": m.group(1)}),
    (re.compile(r"job-boards\.greenhouse\.io/(\w+)", re.I), "greenhouse", lambda m: {"board_token": m.group(1)}),
    (re.compile(r"jobs\.lever\.co/(\w[\w-]+)", re.I), "lever", lambda m: {"company": m.group(1)}),
    (re.compile(r"(\w[\w-]*)\.wd(\d+)\.myworkdayjobs\.com(?:/(?:en-[A-Z]{2}/)?(\w[\w-]*))?", re.I), "workday",
     lambda m: {"tenant": m.group(1), "wd_version": m.group(2), "site_id": m.group(3) or "External_Career_Site"}),
    (re.compile(r"(\w[\w-]*)\.eightfold\.ai", re.I), "eightfold",
     lambda m: {"company": m.group(1), "domain": f"{m.group(1)}.com"}),
    (re.compile(r"api\.ashbyhq\.com/posting-api/job-board/(\w+)", re.I), "ashby", lambda m: {"board_token": m.group(1)}),
    (re.compile(r"jobs\.ashbyhq\.com/(\w[\w-]*)", re.I), "ashby", lambda m: {"board_token": m.group(1)}),
    (re.compile(r"(\w[\w-]*)\.icims\.com", re.I), "icims", lambda m: {"subdomain": m.group(1)}),
    (re.compile(r"api\.smartrecruiters\.com/v1/companies/(\w+)", re.I), "smartrecruiters", lambda m: {"company_id": m.group(1)}),
    (re.compile(r"jobs\.smartrecruiters\.com/(\w[\w-]*)", re.I), "smartrecruiters", lambda m: {"company_id": m.group(1)}),
]

# HTML signatures for each ATS platform
_HTML_SIGNATURES = [
    ("greenhouse", [
        re.compile(r"boards\.greenhouse\.io/(\w+)", re.I),
        re.compile(r"greenhouse\.io/embed", re.I),
        re.compile(r'id="grnhse_app"', re.I),
        re.compile(r'class="[^"]*greenhouse[^"]*"', re.I),
    ]),
    ("lever", [
        re.compile(r"jobs\.lever\.co/(\w[\w-]+)", re.I),
        re.compile(r"lever-jobs-embed", re.I),
        re.compile(r"api\.lever\.co", re.I),
    ]),
    ("workday", [
        re.compile(r"(\w[\w-]*)\.wd(\d+)\.myworkdayjobs\.com", re.I),
        re.compile(r"myworkdayjobs\.com", re.I),
        re.compile(r"workday\.com/.*career", re.I),
    ]),
    ("ashby", [
        re.compile(r"ashbyhq\.com", re.I),
        re.compile(r"ashby-job-posting", re.I),
        re.compile(r"jobs\.ashbyhq\.com/(\w[\w-]*)", re.I),
    ]),
    ("eightfold", [
        re.compile(r"(\w[\w-]*)\.eightfold\.ai", re.I),
    ]),
    ("icims", [
        re.compile(r"(\w[\w-]*)\.icims\.com", re.I),
    ]),
    ("smartrecruiters", [
        re.compile(r"smartrecruiters\.com", re.I),
    ]),
]


def _match_url_patterns(text: str) -> DetectionResult | None:
    """Try all URL patterns against a text string. Returns first match or None."""
    for pattern, ats_type, config_fn in _URL_PATTERNS:
        m = pattern.search(text)
        if m:
            return DetectionResult(
                ats_type=ats_type,
                confidence=0.9,
                config=config_fn(m),
                details=f"pattern: {m.group(0)}",
            )
    return None


async def detect_ats(careers_url: str) -> DetectionResult:
    """
    Multi-strategy ATS detection:
    1. URL pattern matching on the input URL
    2. Fetch page → check final URL after redirects
    3. Scan all <a> hrefs, <iframe> srcs, <script> srcs for ATS patterns
    4. Scan raw HTML/JS for ATS signatures
    5. Blind API probing on common ATS endpoints using company slug
    """
    # Strategy 1: Direct URL pattern matching
    result = _match_url_patterns(careers_url)
    if result:
        result.confidence = 0.95
        result.details = f"URL match: {result.details}"
        return await _probe_api(result)

    # Strategy 2-4: Fetch page and analyze
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENTS[0]},
            timeout=httpx.Timeout(15.0),
            follow_redirects=True,
        ) as client:
            response = await client.get(careers_url)
            html = response.text
            final_url = str(response.url)
    except Exception as e:
        # Can't fetch page — fall through to blind probing
        html = ""
        final_url = careers_url

    # Strategy 2: Check final URL after redirects
    if final_url != careers_url:
        result = _match_url_patterns(final_url)
        if result:
            result.confidence = 0.95
            result.details = f"redirect: {result.details}"
            return await _probe_api(result)

    if html:
        # Strategy 3: Scan all links (href, src) for ATS patterns
        result = _detect_from_links(html)
        if result:
            return await _probe_api(result)

        # Strategy 4: Scan raw HTML/JS text for ATS signatures
        result = _detect_from_html_text(html)
        if result:
            return await _probe_api(result)

    # Strategy 5: Blind API probing using company slug from URL
    slug = _extract_slug_from_url(careers_url)
    if slug:
        result = await _blind_probe(slug)
        if result:
            return result

    return DetectionResult(ats_type="unknown", confidence=0.0, details="No ATS platform detected")


def _detect_from_links(html: str) -> DetectionResult | None:
    """Scan all <a>, <iframe>, <script> tags for ATS URLs."""
    soup = BeautifulSoup(html, "html.parser")

    # Check all link-like attributes
    for tag in soup.find_all(["a", "iframe", "script", "link", "embed"]):
        for attr in ("href", "src", "data-src", "data-url", "action"):
            url = tag.get(attr, "")
            if url:
                result = _match_url_patterns(url)
                if result:
                    result.confidence = 0.9
                    result.details = f"{tag.name}[{attr}]: {result.details}"
                    return result

    return None


def _detect_from_html_text(html: str) -> DetectionResult | None:
    """Scan raw HTML text for ATS signatures."""
    for ats_type, patterns in _HTML_SIGNATURES:
        for p in patterns:
            m = p.search(html)
            if m:
                # Try to extract config using URL patterns on a wider context
                context = html[max(0, m.start() - 50):m.end() + 300]
                result = _match_url_patterns(context)
                if result:
                    result.confidence = 0.75
                    result.details = f"html_text: {result.details}"
                    return result
                # Fallback: return type without config
                return DetectionResult(
                    ats_type=ats_type,
                    confidence=0.5,
                    config={},
                    details=f"html_sig: {m.group(0)}",
                )
    return None


def _extract_slug_from_url(url: str) -> str:
    """Guess company slug from careers URL for blind probing."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    # jobs.company.com or careers.company.com → company
    parts = hostname.split(".")
    if len(parts) >= 2:
        candidate = parts[-2]  # e.g., "netflix" from "jobs.netflix.com"
        if candidate not in ("com", "org", "net", "io", "co", "www"):
            return candidate.lower()
    return ""


async def _blind_probe(slug: str) -> DetectionResult | None:
    """Try common ATS API endpoints using the company slug."""
    probes = [
        ("greenhouse", f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
         {"board_token": slug}, lambda r: "jobs" in r.json()),
        ("lever", f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=1",
         {"company": slug}, lambda r: isinstance(r.json(), list)),
        ("ashby", f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
         {"board_token": slug}, lambda r: "jobs" in r.json()),
        ("eightfold", f"https://{slug}.eightfold.ai/api/pcsx/search?domain={slug}.com&query=&start=0",
         {"company": slug, "domain": f"{slug}.com"}, lambda r: len(r.json().get("data", {}).get("positions", [])) > 0),
    ]

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENTS[0]},
        timeout=httpx.Timeout(connect=5.0, read=60.0, write=5.0, pool=5.0),
    ) as client:
        for ats_type, probe_url, config, validator in probes:
            try:
                response = await client.get(probe_url)
                if response.status_code == 200 and validator(response):
                    return DetectionResult(
                        ats_type=ats_type,
                        confidence=0.85,
                        config=config,
                        details=f"blind_probe: {probe_url}",
                    )
            except Exception:
                continue

    return None


async def _probe_api(result: DetectionResult) -> DetectionResult:
    """Validate detection by probing the actual API endpoint."""
    if not result.config:
        return result
    try:
        from artemis.scrapers.registry import get_scraper
        scraper = get_scraper(result.ats_type, result.config)
        async with scraper:
            jobs = await scraper.scrape(query="", limit=3)
            result.sample_jobs = len(jobs)
            if jobs:
                result.confidence = min(result.confidence + 0.05, 1.0)
                result.details += f" | probe: {len(jobs)} jobs"
            else:
                result.confidence = max(result.confidence - 0.1, 0.0)
                result.details += " | probe: 0 jobs"
    except Exception as e:
        result.confidence = max(result.confidence - 0.2, 0.0)
        result.details += f" | probe_failed: {e}"
    return result
