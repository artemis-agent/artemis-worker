"""Tests for the search-grounded discovery agent."""

from __future__ import annotations


from artemis.discovery.agent import (
    _canonical_careers_url,
    _extract_candidates,
    _host_of,
    _is_noise,
    _looks_like_careers_url,
    _name_compatible,
    _needs_verification,
    _query_domain,
    _AtsCandidate,
    _BODY_ATS_URL_RE,
)
from artemis.discovery.search import SearchResult


# ── _is_noise ─────────────────────────────────────────────────────────────

def test_is_noise_filters_aggregators():
    assert _is_noise("https://www.linkedin.com/jobs/view/123")
    assert _is_noise("https://www.indeed.com/cmp/Stripe")
    assert _is_noise("https://www.glassdoor.com/Jobs/Stripe-Jobs")
    assert _is_noise("https://www.crunchbase.com/organization/stripe")
    assert _is_noise("")


def test_is_noise_allows_real_ats_urls():
    assert not _is_noise("https://boards.greenhouse.io/stripe")
    assert not _is_noise("https://jobs.lever.co/netflix")
    assert not _is_noise("https://disney.wd5.myworkdayjobs.com/en-US/DisneyCareers")


# ── _extract_candidates ───────────────────────────────────────────────────

def _r(url: str, title: str = "T", snippet: str = "S") -> SearchResult:
    return SearchResult(title=title, url=url, snippet=snippet)


def test_extract_greenhouse():
    cands = _extract_candidates([_r("https://boards.greenhouse.io/stripe")])
    assert len(cands) == 1
    assert cands[0].ats == "greenhouse"
    assert cands[0].slug == "stripe"
    assert cands[0].config == {"board_token": "stripe"}


def test_extract_greenhouse_eu_and_job_boards():
    cands = _extract_candidates([
        _r("https://boards.eu.greenhouse.io/spotify"),
        _r("https://job-boards.greenhouse.io/datadog"),
    ])
    assert {c.slug for c in cands} == {"spotify", "datadog"}
    assert all(c.ats == "greenhouse" for c in cands)


def test_extract_lever():
    cands = _extract_candidates([_r("https://jobs.lever.co/netflix")])
    assert cands[0].ats == "lever"
    assert cands[0].config == {"company": "netflix"}


def test_extract_ashby_path_and_subdomain():
    a = _extract_candidates([_r("https://jobs.ashbyhq.com/linear")])
    b = _extract_candidates([_r("https://vercel.ashbyhq.com/jobs")])
    assert a[0].slug == "linear" and a[0].ats == "ashby"
    assert b[0].slug == "vercel" and b[0].ats == "ashby"


def test_extract_workday_with_wd_version():
    cands = _extract_candidates([
        _r("https://disney.wd5.myworkdayjobs.com/en-US/DisneyCareers/job/..."),
    ])
    assert len(cands) == 1
    c = cands[0]
    assert c.ats == "workday"
    assert c.slug == "disney"
    assert c.config["tenant"] == "disney"
    assert c.config["wd_version"] == "5"
    assert c.config["site_id"] == "DisneyCareers"


def test_extract_workday_no_language_prefix():
    """Body fingerprint case: URLs in HTML often omit the /en-US/ prefix.
    Site_id must NOT be treated as a language code when the path is deeper."""
    cands = _extract_candidates([
        _r("https://target.wd5.myworkdayjobs.com/targetcareers"),
        _r("https://target.wd5.myworkdayjobs.com/targetcareers/login?redirect=foo"),
    ])
    # Both URLs are for the same workday board — dedupe to 1 candidate.
    assert len(cands) == 1
    assert cands[0].config["site_id"] == "targetcareers"
    assert cands[0].config["tenant"] == "target"


def test_extract_smartrecruiters():
    cands = _extract_candidates([_r("https://jobs.smartrecruiters.com/Bosch")])
    assert cands[0].ats == "smartrecruiters"
    assert cands[0].config == {"company_id": "Bosch"}  # case preserved


def test_extract_eightfold():
    cands = _extract_candidates([_r("https://microsoft.eightfold.ai/careers")])
    assert cands[0].ats == "eightfold"
    assert cands[0].slug == "microsoft"
    assert cands[0].config == {"company": "microsoft", "domain": "microsoft.com"}


def test_extract_icims():
    cands = _extract_candidates([_r("https://careers-acme.icims.com/jobs/search")])
    assert cands[0].ats == "icims"
    assert cands[0].slug == "careers-acme"


def test_extract_skips_noise_hosts():
    """LinkedIn / Glassdoor / Indeed must NOT yield candidates even if their
    URLs contain ATS-looking text."""
    cands = _extract_candidates([
        _r("https://www.linkedin.com/jobs/view/?greenhouse.io"),
        _r("https://www.glassdoor.com/Jobs/Stripe"),
        _r("https://boards.greenhouse.io/stripe"),
    ])
    # Only the real greenhouse URL should match.
    assert len(cands) == 1
    assert cands[0].slug == "stripe"


def test_extract_dedupes_repeated_urls():
    """The same ATS+slug should only appear once even if multiple results
    point to it."""
    cands = _extract_candidates([
        _r("https://boards.greenhouse.io/stripe"),
        _r("https://boards.greenhouse.io/stripe/jobs/123"),
        _r("https://boards.greenhouse.io/stripe/jobs/456"),
    ])
    assert len(cands) == 1


def test_extract_preserves_search_order():
    """First-occurring ATS in the result list wins (DDG ranks by relevance)."""
    cands = _extract_candidates([
        _r("https://jobs.lever.co/foo"),
        _r("https://boards.greenhouse.io/bar"),
    ])
    assert cands[0].ats == "lever" and cands[0].slug == "foo"
    assert cands[1].ats == "greenhouse" and cands[1].slug == "bar"


# ── _needs_verification ───────────────────────────────────────────────────

def test_needs_verification_short_slug_low_jobs():
    """The Eli-Lilly false-positive shape: short slug + few jobs."""
    cand = _AtsCandidate(ats="ashby", slug="eli", config={}, evidence_url="", job_count=4)
    assert _needs_verification("Eli Lilly", cand) is True


def test_no_verification_for_workday():
    """Workday tenants are short by design (`lilly`, `disney`); the URL itself
    is strong evidence so we skip the LLM verify."""
    cand = _AtsCandidate(
        ats="workday", slug="lilly",
        config={"tenant": "lilly", "site_id": "LillyCareers", "wd_version": "5"},
        evidence_url="https://lilly.wd5.myworkdayjobs.com/en-US/LillyCareers",
        job_count=50,
    )
    assert _needs_verification("Eli Lilly and Company", cand) is False


def test_no_verification_for_long_matching_slug():
    """Andurilindustries on greenhouse — clearly the company itself."""
    cand = _AtsCandidate(
        ats="greenhouse", slug="andurilindustries", config={"board_token": "andurilindustries"},
        evidence_url="", job_count=200,
    )
    assert _needs_verification("Anduril Industries", cand) is False


def test_no_verification_for_high_job_count():
    """A short slug with hundreds of jobs is unlikely to be a generic collision."""
    cand = _AtsCandidate(
        ats="greenhouse", slug="fox", config={}, evidence_url="", job_count=300,
    )
    assert _needs_verification("Fox Corporation", cand) is False


# ── _name_compatible ─────────────────────────────────────────────────────

def test_name_compatible_exact_and_substring():
    assert _name_compatible("Stripe", "stripe")
    assert _name_compatible("Anduril Industries", "andurilindustries")
    assert _name_compatible("Anduril Industries", "anduril")
    assert _name_compatible("Eli Lilly", "lilly")
    assert _name_compatible("Charles Schwab", "schwab")
    assert _name_compatible("Target", "target")
    # Token-level via camelCase / hyphen split.
    assert _name_compatible("TRM Labs", "trm-labs")
    assert _name_compatible("Take-Two Interactive", "taketwointeractive")
    assert _name_compatible("Disc Medicine", "discmedicine")


def test_name_compatible_rejects_collisions():
    """Historic false-positives we must NEVER accept."""
    # Costco search returned Unilever's Workday tenant — no shared token.
    assert not _name_compatible("Costco", "unilever")
    # Apple/Tesla nonsense.
    assert not _name_compatible("Apple", "google")
    assert not _name_compatible("Tesla", "ford")
    # Riverside startup got matched to Riverside Healthcare iCIMS subdomain.
    assert not _name_compatible("Riverside", "employees-riversidehealthcare")
    # Draiven got matched to DrivenMotorJobsLimited — the lazy 4-char
    # window check used to accept this because "iven" overlaps. Must reject.
    assert not _name_compatible("Draiven", "DrivenMotorJobsLimited")
    # Eli Lilly's ashby "eli" hit — 3 chars, fails the length guard.
    assert not _name_compatible("Eli Lilly", "eli")
    # Generic short tokens that aren't the company.
    assert not _name_compatible("US Foods", "us")
    assert not _name_compatible("General Motors", "general")


# ── _looks_like_careers_url ──────────────────────────────────────────────

def test_looks_like_careers_url_positive_cases():
    assert _looks_like_careers_url("https://corporate.target.com/careers", "Target")
    assert _looks_like_careers_url("https://jobs.target.com", "Target")
    assert _looks_like_careers_url("https://careers.costco.com", "Costco")
    assert _looks_like_careers_url("https://www.disneycareers.com", "Disney")


def test_looks_like_careers_url_rejects_noise():
    # LinkedIn / Glassdoor must not be fingerprinted even if path says /careers.
    assert not _looks_like_careers_url("https://www.linkedin.com/jobs", "Target")
    assert not _looks_like_careers_url("https://www.glassdoor.com/Jobs/Target", "Target")


def test_looks_like_careers_url_rejects_wrong_company():
    # Apple's careers page should not be fingerprinted when searching for Target.
    assert not _looks_like_careers_url("https://jobs.apple.com", "Target")


# ── _canonical_careers_url ───────────────────────────────────────────────

def test_canonical_careers_url_strips_job_id():
    """Regression: the agent used to write the search-evidence URL straight
    into `careers_url`, leaking job-level deep links like
    `https://job-boards.greenhouse.io/revel/jobs/5622076004`."""
    assert _canonical_careers_url("greenhouse", "revel", {"board_token": "revel"}) == \
        "https://job-boards.greenhouse.io/revel"
    assert _canonical_careers_url("lever", "stripe", {"company": "stripe"}) == \
        "https://jobs.lever.co/stripe"
    assert _canonical_careers_url("ashby", "linear", {"board_token": "linear"}) == \
        "https://jobs.ashbyhq.com/linear"
    # SmartRecruiters preserves case from the config.
    assert _canonical_careers_url("smartrecruiters", "adobe", {"company_id": "Adobe1"}) == \
        "https://careers.smartrecruiters.com/Adobe1"


def test_canonical_careers_url_workday_uses_full_tenant_path():
    assert _canonical_careers_url(
        "workday", "anchorglass",
        {"tenant": "anchorglass", "site_id": "Careers", "wd_version": "1"},
    ) == "https://anchorglass.wd1.myworkdayjobs.com/Careers"


def test_canonical_careers_url_passthrough_for_self_describing_ats():
    # iCIMS stores its careers landing in the config directly.
    assert _canonical_careers_url(
        "icims", "audacy",
        {"careers_url": "https://careers-audacy.icims.com/jobs/search"},
    ) == "https://careers-audacy.icims.com/jobs/search"
    # Eightfold uses the configured domain.
    assert _canonical_careers_url(
        "eightfold", "microsoft", {"domain": "careers.microsoft.com"},
    ) == "https://careers.microsoft.com/careers"


# ── _query_domain ────────────────────────────────────────────────────

def test_query_domain_handles_common_inputs():
    # Full URL with scheme + www + path.
    assert _query_domain("https://www.yubico.com/careers") == "yubico.com"
    # Scheme + apex.
    assert _query_domain("https://yubico.com") == "yubico.com"
    # Bare host with www.
    assert _query_domain("www.yubico.com") == "yubico.com"
    # Bare apex.
    assert _query_domain("yubico.com") == "yubico.com"
    # Subdomain preserved (search anchor is fine either way).
    assert _query_domain("https://careers.yubico.com") == "careers.yubico.com"
    # Empty / None → empty (caller falls back to name-anchored queries).
    assert _query_domain(None) == ""
    assert _query_domain("") == ""
    assert _query_domain("   ") == ""


def test_host_of_strips_scheme_and_www():
    assert _host_of("https://www.target.com/careers") == "target.com"
    assert _host_of("http://jobs.lever.co/foo") == "jobs.lever.co"


# ── _BODY_ATS_URL_RE (fingerprint pattern) ────────────────────────────────

def test_body_regex_extracts_workday_from_html():
    """The Target case: corporate.target.com/careers HTML embeds the full
    Workday URL inside an anchor — our regex must catch it."""
    body = (
        '<html><body><a href="https://target.wd5.myworkdayjobs.com/'
        'targetcareers">View jobs</a></body></html>'
    )
    hits = [m.group(0) for m in _BODY_ATS_URL_RE.finditer(body)]
    assert any("target.wd5.myworkdayjobs.com/targetcareers" in h for h in hits)


def test_body_regex_extracts_multiple_ats_systems():
    body = """
    <script src="https://boards.greenhouse.io/embed/job_board?for=stripe"></script>
    <iframe src="https://jobs.lever.co/netflix/12345"></iframe>
    <link href="https://careers-acme.icims.com/jobs/search">
    """
    hits = {m.group(0) for m in _BODY_ATS_URL_RE.finditer(body)}
    assert any("greenhouse.io" in h and "stripe" in h for h in hits)
    assert any("jobs.lever.co/netflix" in h for h in hits)
    assert any("careers-acme.icims.com" in h for h in hits)


def test_body_regex_ignores_unrelated_urls():
    body = '<a href="https://www.google.com/search?q=jobs">search</a>'
    assert [m.group(0) for m in _BODY_ATS_URL_RE.finditer(body)] == []
