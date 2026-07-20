"""AI-powered career-site discovery agent.

Strategy
--------
1. Search "{company} careers" via free DuckDuckGo.
2. Regex-extract `(ats_type, slug/tenant)` from any result URL matching one
   of the 7 supported ATS URL patterns. This catches Workday and iCIMS for
   free — the big win over the brute-force probe.
3. Probe the extracted candidate against the live ATS API to confirm jobs
   exist (reuses per-ATS probe functions from `probe.py`).
4. LLM fallback: when no URL matches a known pattern, feed the top-10
   snippets to GPT-4 and let it identify the ATS + slug.
5. LLM verify: when the matched slug is suspiciously short, ask the LLM to
   confirm the board actually belongs to the requested company. Kills the
   false-positive collisions that plagued the brute-force probe (e.g.
   Eli Lilly → "eli" → unrelated 4-job Ashby board).
6. Write YAML to `configs/companies/{slug}.yaml`, same shape as `probe.py`.

Single public entry point: `discover_company(name, website=None)`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import pathlib
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx
import yaml

from artemis.core.ai import get_ai_client
from artemis.core.config import settings
from artemis.core.prompts import EXTRACT_ATS_FROM_SEARCH, VERIFY_COMPANY_MATCH
from artemis.discovery import probe as probe_mod
from artemis.discovery.search import (
    SearchResult,
    WebSearch,
    default_searcher,
)


logger = logging.getLogger("artemis.discovery.agent")

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# ── URL patterns ──────────────────────────────────────────────────────────
# Each pattern, when matched, produces an `_AtsCandidate`. Order matters:
# we try more-specific patterns first.
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("greenhouse", re.compile(r"https?://boards(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([a-z0-9_-]+)", re.I)),
    ("greenhouse", re.compile(r"https?://job-boards(?:\.eu)?\.greenhouse\.io/([a-z0-9_-]+)", re.I)),
    ("lever",      re.compile(r"https?://jobs\.(?:eu\.)?lever\.co/([a-z0-9_-]+)", re.I)),
    ("ashby",      re.compile(r"https?://jobs\.ashbyhq\.com/([a-z0-9_-]+)", re.I)),
    ("ashby",      re.compile(r"https?://([a-z0-9_-]+)\.ashbyhq\.com", re.I)),
    # Workday: optional 2-3-letter language prefix (e.g. `en-US/`, `wt-WT/`)
    # but NOT a deeper site path (which would eat the real site_id).
    ("workday",    re.compile(r"https?://([a-z0-9_-]+)\.wd(\d)\.myworkdayjobs\.com/(?:[a-z]{2,3}(?:-[A-Z]{2,4})?/)?([A-Za-z0-9_]+)", re.I)),
    ("workday",    re.compile(r"https?://([a-z0-9_-]+)\.myworkdayjobs\.com/(?:[a-z]{2,3}(?:-[A-Z]{2,4})?/)?([A-Za-z0-9_]+)", re.I)),
    ("smartrecruiters", re.compile(r"https?://(?:jobs|careers)\.smartrecruiters\.com/([A-Za-z0-9_.-]+)", re.I)),
    ("eightfold",  re.compile(r"https?://([a-z0-9_-]+)\.eightfold\.ai", re.I)),
    ("icims",      re.compile(r"https?://(careers-[a-z0-9_-]+)\.icims\.com", re.I)),
    ("icims",      re.compile(r"https?://([a-z0-9_-]+)\.icims\.com", re.I)),
]

# Aggregator / noise domains we never want to extract from.
_NOISE_HOSTS = {
    "linkedin.com", "indeed.com", "glassdoor.com", "ziprecruiter.com",
    "monster.com", "simplyhired.com", "wellfound.com", "angel.co",
    "builtin.com", "themuse.com", "y-combinator.com", "ycombinator.com",
    "crunchbase.com", "techcrunch.com", "wikipedia.org", "wikimedia.org",
    "facebook.com", "twitter.com", "x.com", "youtube.com", "instagram.com",
    "google.com", "bing.com", "duckduckgo.com",
}

# Regexes for extracting ATS URLs out of arbitrary HTML response bodies.
# Used by the fingerprint pass to catch white-labeled careers pages
# (e.g. `corporate.target.com/careers` whose HTML embeds a link to
# `target.wd5.myworkdayjobs.com/targetcareers`).
_BODY_ATS_URL_RE = re.compile(
    r"https?://[a-z0-9_.-]+\."
    r"(?:greenhouse\.io|lever\.co|ashbyhq\.com|myworkdayjobs\.com|"
    r"smartrecruiters\.com|eightfold\.ai|icims\.com)"
    r"[/A-Za-z0-9_.?=&-]*",
    re.I,
)

# Browser-ish headers — careers pages occasionally 403 a bare `httpx` UA.
_BROWSER_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}


@dataclass
class _AtsCandidate:
    ats: str
    slug: str
    config: dict
    evidence_url: str
    # Filled in after probe:
    job_count: int = 0
    matched_slug: str = ""  # the slug we used to probe (may differ for workday)


@dataclass
class DiscoveryResult:
    """Outcome of `discover_company`. `status` is one of:
    `discovered` | `unverified` | `not_found` | `already_known` | `error`."""
    name: str
    slug: str
    status: str
    ats: Optional[str] = None
    careers_url: Optional[str] = None
    ats_config: Optional[dict] = None
    discovered_jobs: int = 0
    discovered_from: str = "agent"
    evidence_url: Optional[str] = None
    llm_calls: int = 0
    search_calls: int = 0
    elapsed_sec: float = 0.0
    error: Optional[str] = None

    def to_yaml_dict(self) -> dict:
        """Emit the canonical config schema (matches scripts/normalize_configs.py)."""
        return {
            "name": self.name,
            "slug": self.slug,
            "ats": self.ats or "",
            "ats_config": self.ats_config or {},
            "careers_url": self.careers_url or "",
            "verified": True,
            "discovered_from": self.discovered_from,
            "discovered_jobs": int(self.discovered_jobs or 0),
            "last_verified": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "evidence_url": self.evidence_url,
        }


# ── Helpers ───────────────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _flat(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


# Generic single-word slugs that are token-fragments of many unrelated
# company names. When a slug matches ONLY by being a token of a multi-word
# company name (e.g. "General" in "General Motors"), reject it — those
# generic slugs were the original source of false-positive collisions
# (`general`, `us`, `new`, `central` → matched dozens of unrelated boards).
_GENERIC_TOKENS = {
    "the", "and", "a", "an", "of", "for", "in", "on", "at", "to", "by",
    "us", "uk", "eu", "usa", "new", "old", "all", "any", "big", "small",
    "first", "second", "last", "next", "best", "top",
    "general", "national", "international", "global", "world", "central",
    "north", "south", "east", "west", "american", "european", "global",
    "united", "alliance", "industry", "industries", "group", "co",
    "company", "corp", "corporation", "ltd", "inc", "llc", "holdings",
    "ventures", "partners", "capital", "labs", "lab", "studio", "studios",
    "systems", "solutions", "services", "consulting", "media", "tech",
    "digital", "online", "data", "cloud", "core", "main", "prime",
}


def _name_compatible(name: str, slug: str) -> bool:
    """Strict sanity check that `slug` plausibly belongs to `name`.

    Accepts only strong signals; everything else falls through to the LLM
    verify step. Rejected examples:
      Costco           vs unilever              (no token overlap)
      Riverside        vs employees-riversidehealthcare  (no shared token)
      Draiven          vs DrivenMotorJobsLimited         (no shared token;
                                                          "iven" overlap is
                                                          NOT enough)
      General Motors   vs general               (token is too generic)
    Accepted examples:
      Stripe                 vs stripe                  (exact)
      Anduril Industries     vs andurilindustries       (flat-name match)
      Anduril Industries     vs anduril                 (specific token match)
      Eli Lilly              vs lilly  (workday tenant) (specific token match)
      Charles Schwab         vs schwab                  (specific token match)
      TRM Labs               vs trm-labs                (flat-name match)
    """
    nf = _flat(name)
    sf = _flat(slug)
    if not nf or not sf:
        return False
    # 1. Exact match (best signal — single-word name like "Stripe" → "stripe").
    if nf == sf:
        return True
    # 2. Slug starts with the whole flat name (handles `andurilindustries`,
    #    `veeamsoftware`, etc.).
    if len(nf) >= 4 and sf.startswith(nf):
        return True
    # 3. Slug equals one of the multi-char *specific* tokens of the company
    #    name. Generic tokens like "general"/"us"/"new" are rejected because
    #    they're too widely shared to uniquely identify any company.
    name_tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9]+", name)]
    if sf in name_tokens and len(sf) >= 4 and sf not in _GENERIC_TOKENS:
        return True
    # 4. Token-level overlap on hyphen/case boundaries. Catches slugs that
    #    embed the company name as a separate word (e.g. "trm-labs" for
    #    "TRM Labs") while still rejecting unrelated multi-word slugs.
    slug_tokens = [t.lower() for t in re.findall(r"[A-Z][a-z0-9]*|[a-z0-9]+", slug)]
    overlap = {
        t for t in slug_tokens
        if len(t) >= 4 and t in name_tokens and t not in _GENERIC_TOKENS
    }
    if overlap:
        return True
    return False


def _host_of(url: str) -> str:
    m = re.match(r"https?://(?:www\.)?([a-z0-9.-]+)", url.lower())
    return m.group(1) if m else ""


def _query_domain(website: str | None) -> str:
    """Best-effort ‘bare apex domain’ for use in a search query.

    Accepts anything callers tend to pass us — full URLs
    (`https://www.yubico.com/careers`), schemeless URLs (`yubico.com/jobs`),
    or even just a host (`www.yubico.com`). Returns `"yubico.com"` or `""`
    if nothing usable can be salvaged. The domain is then used to anchor
    search queries (`yubico.com careers`) which are much more selective
    than name-only queries for ambiguous names."""
    if not website:
        return ""
    raw = website.strip().lower()
    if not raw.startswith("http"):
        raw = "https://" + raw
    return _host_of(raw)


def _canonical_careers_url(ats: str, slug: str, config: dict) -> str:
    """Public landing URL for the board — NOT a job-level deep link.

    The agent's `evidence_url` is whatever search result we found (often a
    specific posting like `.../jobs/5622076004`). The persisted
    `careers_url` must be the board root so the worker / humans can re-visit
    it. Each ATS has a deterministic public board URL keyed off the slug or
    its config."""
    cfg = config or {}
    if ats == "greenhouse":
        token = cfg.get("board_token") or slug
        return f"https://job-boards.greenhouse.io/{token}"
    if ats == "lever":
        company = cfg.get("company") or slug
        return f"https://jobs.lever.co/{company}"
    if ats == "ashby":
        token = cfg.get("board_token") or slug
        return f"https://jobs.ashbyhq.com/{token}"
    if ats == "smartrecruiters":
        # Case-sensitive — preserve whatever the candidate captured.
        company_id = cfg.get("company_id") or slug
        return f"https://careers.smartrecruiters.com/{company_id}"
    if ats == "workday":
        tenant = cfg.get("tenant") or slug
        site_id = cfg.get("site_id") or ""
        wd = cfg.get("wd_version") or "5"
        if tenant and site_id:
            return f"https://{tenant}.wd{wd}.myworkdayjobs.com/{site_id}"
        return f"https://{tenant}.wd{wd}.myworkdayjobs.com"
    if ats == "eightfold":
        domain = cfg.get("domain") or f"{slug}.com"
        return f"https://{domain}/careers"
    if ats == "icims":
        # iCIMS already stores the careers landing in `careers_url`.
        return cfg.get("careers_url") or f"https://{slug}.icims.com/jobs/search"
    return ""


def _looks_like_careers_url(url: str, name: str) -> bool:
    """True if URL looks like the company's own careers landing page —
    used to pick fingerprint candidates from search results."""
    if not url or _is_noise(url):
        return False
    host = _host_of(url)
    if not host:
        return False
    # The host or path should reference careers/jobs.
    path_hint = re.search(r"/(?:careers?|jobs?|work)(?:[/?]|$)", url.lower())
    host_hint = (
        host.startswith("careers.") or host.startswith("jobs.")
        or host.startswith("career.") or host.startswith("corporate.")
        or "careers" in host or "jobs" in host
    )
    if not (path_hint or host_hint):
        return False
    # Must plausibly belong to the named company — strip the leading
    # subdomain so "careers.lilly.com" → check "lilly" + "lilly.com".
    stripped = re.sub(r"^[a-z0-9-]+\.", "", host)
    root = stripped.split(".")[0] if "." in stripped else host
    return _name_compatible(name, root) or _name_compatible(name, host)


def _is_noise(url: str) -> bool:
    if not url:
        return True
    m = re.match(r"https?://(?:www\.)?([a-z0-9.-]+)", url.lower())
    if not m:
        return True
    host = m.group(1)
    return any(host == n or host.endswith("." + n) for n in _NOISE_HOSTS)


def _extract_candidates(results: list[SearchResult]) -> list[_AtsCandidate]:
    """Walk results, regex-match each URL against the 7 ATS patterns.
    Returns candidates in result-order (DDG already ranks by relevance)."""
    out: list[_AtsCandidate] = []
    seen: set[tuple[str, str]] = set()
    for r in results:
        url = r.url or ""
        if _is_noise(url):
            continue
        for ats, pat in _PATTERNS:
            m = pat.search(url)
            if not m:
                continue
            if ats == "workday":
                tenant = m.group(1).lower()
                # Pattern with wd-version group (3 captures) vs. without (2 captures).
                if pat.groups == 3:
                    wd_version = m.group(2)
                    site_id = m.group(3)
                else:
                    wd_version = "5"
                    site_id = m.group(2)
                key = (ats, f"{tenant}/{site_id}")
                if key in seen:
                    continue
                seen.add(key)
                out.append(_AtsCandidate(
                    ats=ats,
                    slug=tenant,
                    config={"tenant": tenant, "site_id": site_id, "wd_version": wd_version},
                    evidence_url=url,
                ))
                break
            elif ats == "eightfold":
                slug = m.group(1).lower()
                key = (ats, slug)
                if key in seen:
                    continue
                seen.add(key)
                out.append(_AtsCandidate(
                    ats=ats,
                    slug=slug,
                    config={"company": slug, "domain": f"{slug}.com"},
                    evidence_url=url,
                ))
                break
            elif ats == "icims":
                slug = m.group(1).lower()
                key = (ats, slug)
                if key in seen:
                    continue
                seen.add(key)
                out.append(_AtsCandidate(
                    ats=ats,
                    slug=slug,
                    config={"careers_url": f"https://{slug}.icims.com/jobs/search"},
                    evidence_url=url,
                ))
                break
            else:
                slug = m.group(1).lower()
                key = (ats, slug)
                if key in seen:
                    continue
                seen.add(key)
                cfg = {
                    "greenhouse": {"board_token": slug},
                    "lever": {"company": slug},
                    "ashby": {"board_token": slug},
                    "smartrecruiters": {"company_id": m.group(1)},  # SR is case-sensitive
                }[ats]
                out.append(_AtsCandidate(ats=ats, slug=slug, config=cfg, evidence_url=url))
                break
    return out


async def _probe_candidate(
    client: httpx.AsyncClient,
    cand: _AtsCandidate,
    sem,
) -> _AtsCandidate | None:
    """Hit the live ATS API; populate job_count if successful."""
    fn_by_ats = {
        "greenhouse": lambda: probe_mod.probe_greenhouse(client, cand.slug, sem),
        "lever":      lambda: probe_mod.probe_lever(client, cand.slug, sem),
        "ashby":      lambda: probe_mod.probe_ashby(client, cand.slug, sem),
        "smartrecruiters": lambda: probe_mod.probe_smartrecruiters(client, cand.slug, sem),
        "eightfold":  lambda: probe_mod.probe_eightfold(client, cand.slug, sem),
        "workday":    lambda: probe_mod.probe_workday(
            client, cand.config["tenant"], cand.config["site_id"],
            cand.config.get("wd_version", "5"), sem,
        ),
        "icims":      lambda: probe_mod.probe_icims(client, cand.slug, sem),
    }
    fn = fn_by_ats.get(cand.ats)
    if fn is None:
        return None
    try:
        hit = await fn()
    except Exception as e:
        logger.debug(f"probe {cand.ats}/{cand.slug} raised: {e}")
        return None
    if not hit:
        return None
    _ats, _cfg, count = hit
    cand.job_count = int(count or 0)
    cand.matched_slug = cand.slug
    return cand


async def _fingerprint_careers_page(
    client: httpx.AsyncClient, url: str,
) -> list[_AtsCandidate]:
    """Fetch a candidate careers URL and harvest ATS candidates from it.

    Two signals are inspected:
      1. The redirect destination — many `jobs.X.com` white-label hosts
         301 to the underlying ATS URL.
      2. The response HTML body — even when there is no redirect, the
         careers page typically links to its real ATS (`corporate.target.com/careers`
         body embeds `target.wd5.myworkdayjobs.com/targetcareers`).

    Both signals are funneled through the same `_extract_candidates`
    pipeline used for organic search results, so the existing 7 ATS
    regexes do all the work.
    """
    try:
        r = await client.get(url, headers=_BROWSER_HEADERS, timeout=12)
    except Exception:
        return []
    # Read at most ~200KB of body — careers pages are usually thin shells.
    body = r.text[:200_000] if r.status_code < 400 else ""

    found: dict[str, SearchResult] = {}
    final = str(r.url)
    found[final] = SearchResult(title="", url=final, snippet="")
    if body:
        for m in _BODY_ATS_URL_RE.finditer(body):
            u = m.group(0)
            found.setdefault(u, SearchResult(title="", url=u, snippet=""))
    return _extract_candidates(list(found.values()))


async def _sample_titles(client: httpx.AsyncClient, cand: _AtsCandidate, n: int = 5) -> list[str]:
    """Best-effort fetch of N job titles from the matched board for LLM verification."""
    try:
        if cand.ats == "greenhouse":
            r = await client.get(
                f"https://boards-api.greenhouse.io/v1/boards/{cand.slug}/jobs",
                timeout=10,
            )
            if r.status_code == 200:
                return [j.get("title", "")[:120] for j in (r.json().get("jobs") or [])[:n]]
        elif cand.ats == "lever":
            r = await client.get(
                f"https://api.lever.co/v0/postings/{cand.slug}?mode=json&limit={n}",
                timeout=10,
            )
            if r.status_code == 200 and isinstance(r.json(), list):
                return [j.get("text", "")[:120] for j in r.json()[:n]]
        elif cand.ats == "ashby":
            r = await client.get(
                f"https://api.ashbyhq.com/posting-api/job-board/{cand.slug}",
                timeout=10,
            )
            if r.status_code == 200:
                return [j.get("title", "")[:120] for j in (r.json().get("jobs") or [])[:n]]
    except Exception:
        pass
    return []


async def _llm_extract_from_search(
    company_name: str, results: list[SearchResult]
) -> _AtsCandidate | None:
    """Fallback when no regex pattern matched: ask GPT-4 to identify the ATS + slug
    from the search snippets. Returns a candidate or None."""
    if not results:
        return None
    snippet_block = "\n".join(
        f"{i+1}. {r.title}\n   URL: {r.url}\n   {r.snippet[:240]}"
        for i, r in enumerate(results[:10])
    )
    prompt = EXTRACT_ATS_FROM_SEARCH.format(
        company_name=company_name, results=snippet_block
    )
    try:
        client = get_ai_client()
        resp = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
    except Exception as e:
        logger.debug(f"LLM extract failed for {company_name}: {e}")
        return None

    ats = (data.get("ats") or "").lower()
    cfg = data.get("config") or {}
    evidence = data.get("evidence_url") or ""
    if ats not in {
        "greenhouse", "lever", "ashby", "workday",
        "smartrecruiters", "eightfold", "icims",
    } or not cfg:
        return None

    slug = (
        cfg.get("board_token")
        or cfg.get("company_id")          # smartrecruiters canonical
        or cfg.get("tenant")              # workday canonical
        or cfg.get("company")             # lever / eightfold canonical
        or cfg.get("site")                # tolerate old `site` key from older LLM outputs
        or ""
    )
    if not slug:
        return None
    return _AtsCandidate(ats=ats, slug=str(slug).lower(), config=cfg, evidence_url=evidence)


async def _llm_verify_match(
    company_name: str, cand: _AtsCandidate, titles: list[str]
) -> bool:
    """Confirm the board actually belongs to the requested company."""
    if not titles:
        # No titles available — be conservative: only reject when slug
        # is suspiciously short.
        return len(cand.slug) >= 5
    title_block = "\n".join(f"- {t}" for t in titles[:5])
    prompt = VERIFY_COMPANY_MATCH.format(
        company_name=company_name,
        ats=cand.ats,
        slug=cand.slug,
        job_count=cand.job_count,
        titles=title_block,
    )
    try:
        client = get_ai_client()
        resp = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        return bool(data.get("is_match"))
    except Exception as e:
        logger.debug(f"LLM verify failed for {company_name}: {e}")
        # Fail safe — keep the hit when the LLM call errors out.
        return True


def _needs_verification(name: str, cand: _AtsCandidate) -> bool:
    """Trigger LLM verification when the slug is short relative to the
    name AND the job count is small enough to be a generic collision."""
    flat = re.sub(r"[^a-z0-9]+", "", name.lower())
    short = len(cand.slug) < max(5, int(len(flat) * 0.6))
    # Workday tenant is usually short by design ("disney", "lilly"); the
    # tenant being in the URL is itself strong evidence. Skip verify.
    if cand.ats == "workday":
        return False
    return short and cand.job_count <= 25


def _save_yaml(result: DiscoveryResult) -> None:
    configs_dir = pathlib.Path(settings.configs_dir)
    configs_dir.mkdir(parents=True, exist_ok=True)
    path = configs_dir / f"{result.slug}.yaml"
    with open(path, "w") as f:
        yaml.dump(result.to_yaml_dict(), f, default_flow_style=False, sort_keys=False)
    logger.info(f"agent: wrote {path}")


# ── Public entry point ────────────────────────────────────────────────────

async def discover_company(
    name: str,
    website: str | None = None,
    *,
    searcher: WebSearch | None = None,
    http_client: httpx.AsyncClient | None = None,
    dry_run: bool = False,
) -> DiscoveryResult:
    """Find a company's ATS, validate it, and (unless dry_run) write the
    YAML config. Returns a DiscoveryResult with status + cost telemetry."""
    started = time.time()
    slug = _slugify(name)
    result = DiscoveryResult(name=name, slug=slug, status="not_found")

    # Skip if YAML already exists.
    if (pathlib.Path(settings.configs_dir) / f"{slug}.yaml").exists():
        result.status = "already_known"
        result.elapsed_sec = time.time() - started
        return result

    searcher = searcher or default_searcher()
    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(
        headers={"User-Agent": UA}, follow_redirects=True, timeout=15.0,
    )

    try:
        # 1. Search — prefer a domain-anchored query when we have a
        #    website (`yubico.com careers` returns far less noise than
        #    `Yubico careers` for ambiguous names), then fall back to a
        #    name-anchored query because some ATS pages (notably Ashby
        #    and Lever boards) do not embed the company's website domain
        #    in their HTML and would otherwise be missed.
        all_results: list[SearchResult] = []
        domain = _query_domain(website)
        if domain:
            queries: tuple[str, ...] = (
                f"{domain} careers",
                f'"{name}" jobs',
            )
        else:
            queries = (f'"{name}" careers', f"{name} jobs")
        for i, q_template in enumerate(queries):
            if i > 0:
                # Polite gap between consecutive searches to give DDG's
                # backend rotation a chance to recover from rate-limits.
                await asyncio.sleep(2.0)
            results = await searcher.search(q_template, max_results=10)
            result.search_calls += 1
            all_results.extend(results)
            cands = _extract_candidates(results)
            # Drop candidates whose slug doesn't share any 4-char window
            # with the company name (kills cross-company collisions like
            # Costco → Unilever's Workday board).
            cands = [c for c in cands if _name_compatible(name, c.slug)]
            if cands:
                candidates = cands
                break
        else:
            candidates = []
            results = all_results

        # 3. Probe candidates in order; first verified hit wins.
        sem = asyncio.Semaphore(5)
        verified: _AtsCandidate | None = None
        for cand in candidates:
            hit = await _probe_candidate(client, cand, sem)
            if hit is None:
                continue
            # 5. LLM verify only when slug is suspiciously short.
            if _needs_verification(name, hit):
                titles = await _sample_titles(client, hit)
                if not await _llm_verify_match(name, hit, titles):
                    result.llm_calls += 1
                    logger.info(f"agent: rejected {hit.ats}/{hit.slug} for {name} (verify=false)")
                    continue
                result.llm_calls += 1
            verified = hit
            break

        # 4. Fingerprint pass — fetch likely careers URLs from the search
        # results and extract ATS refs from their HTML body / redirect.
        # Catches white-labeled careers pages like `corporate.target.com/careers`
        # that embed `target.wd5.myworkdayjobs.com/targetcareers`.
        if verified is None:
            seen_hosts: set[str] = set()
            fp_targets: list[str] = []
            for r in (all_results or results):
                if not _looks_like_careers_url(r.url, name):
                    continue
                host = _host_of(r.url)
                if host in seen_hosts:
                    continue
                seen_hosts.add(host)
                fp_targets.append(r.url)
                if len(fp_targets) >= 5:
                    break
            for u in fp_targets:
                fp_cands = await _fingerprint_careers_page(client, u)
                fp_cands = [c for c in fp_cands if _name_compatible(name, c.slug)]
                if not fp_cands:
                    continue
                for cand in fp_cands:
                    hit = await _probe_candidate(client, cand, sem)
                    if hit is None:
                        continue
                    if _needs_verification(name, hit):
                        titles = await _sample_titles(client, hit)
                        if not await _llm_verify_match(name, hit, titles):
                            result.llm_calls += 1
                            continue
                        result.llm_calls += 1
                    verified = hit
                    logger.info(f"agent: fingerprint hit {hit.ats}/{hit.slug} for {name} via {u}")
                    break
                if verified is not None:
                    break

        # 5. LLM fallback — only when both search and fingerprint failed
        # and we have nothing else to try.
        if verified is None and not candidates:
            llm_cand = await _llm_extract_from_search(name, all_results or results)
            result.llm_calls += 1
            if llm_cand is not None and _name_compatible(name, llm_cand.slug):
                hit = await _probe_candidate(client, llm_cand, sem)
                if hit is not None:
                    if _needs_verification(name, hit):
                        titles = await _sample_titles(client, hit)
                        if await _llm_verify_match(name, hit, titles):
                            verified = hit
                        result.llm_calls += 1
                    else:
                        verified = hit

        # 6. Write
        if verified is not None:
            result.status = "discovered"
            result.ats = verified.ats
            result.ats_config = verified.config
            result.evidence_url = verified.evidence_url
            # careers_url is the board *landing page*, never the job-level
            # link we happened to find via search.
            canonical = _canonical_careers_url(verified.ats, verified.slug, verified.config)
            result.careers_url = canonical or website or verified.evidence_url or ""
            result.discovered_jobs = verified.job_count
            if not dry_run:
                _save_yaml(result)
        else:
            result.status = "not_found"

    except Exception as e:
        logger.exception(f"agent: error discovering {name}")
        result.status = "error"
        result.error = str(e)
    finally:
        if owns_client:
            await client.aclose()
        result.elapsed_sec = time.time() - started

    return result
