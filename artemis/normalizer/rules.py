"""Rule-based job normalization — no LLM needed for structured ATS data."""

import re

from artemis.normalizer.skill_taxonomy import SKILL_TAXONOMY


# ── Skill extraction ──────────────────────────────────────────────────────

# Precompute patterns: map regex → canonical name for multi-word skills
_SKILL_PATTERNS: list[tuple[re.Pattern, str]] = []
_SKILL_EXACT: dict[str, str] = {}  # lowercase → canonical


def _build_skill_patterns():
    """Build regex patterns for skill extraction from job descriptions."""
    for entry in SKILL_TAXONOMY:
        canonical = entry["canonical"]
        all_names = [canonical] + entry["aliases"]
        for name in all_names:
            lower = name.lower()
            if len(lower) <= 2 or lower in ("go", "r"):
                # Short names need word boundary + context to avoid false positives
                _SKILL_PATTERNS.append((re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE), canonical))
            else:
                _SKILL_EXACT[lower] = canonical


_build_skill_patterns()


def extract_skills_from_text(text: str) -> list[str]:
    """Extract canonical skill names from job description text."""
    if not text:
        return []
    text_lower = text.lower()
    found: dict[str, bool] = {}

    # Exact substring matches (fast path for most skills)
    for alias_lower, canonical in _SKILL_EXACT.items():
        if alias_lower in text_lower:
            found[canonical] = True

    # Regex matches for short/ambiguous names
    for pattern, canonical in _SKILL_PATTERNS:
        if canonical not in found and pattern.search(text):
            found[canonical] = True

    return list(found.keys())


# Seniority detection from title
SENIORITY_PATTERNS = [
    (r"\b(intern(ship)?)\b", "intern"),
    (r"\b(junior|jr\.?|entry[\s-]level|new\s+grad|associate)\b", "junior"),
    (r"\b(mid[\s-]level|mid)\b", "mid"),
    (r"\b(senior|sr\.?)\b", "senior"),
    (r"\b(staff)\b", "staff"),
    (r"\b(principal|distinguished)\b", "principal"),
    (r"\b(director)\b", "director"),
    (r"\b(vp|vice\s+president)\b", "vp"),
    (r"\b(c-level|cto|ceo|cfo|coo|chief)\b", "c-level"),
    (r"\b(lead|head\s+of|manager)\b", "senior"),
]

# Department detection from title/department field
DEPARTMENT_MAP = {
    "engineering": [
        "engineer",
        "developer",
        "software",
        "sre",
        "devops",
        "infrastructure",
        "platform",
        "backend",
        "frontend",
        "fullstack",
        "full-stack",
        "mobile",
        "embedded",
        "firmware",
        "qa",
        "quality",
    ],
    "product": ["product manager", "product owner", "product lead", "product director"],
    "design": ["designer", "ux", "ui", "creative", "brand"],
    "data": ["data scientist", "data engineer", "data analyst", "analytics", "machine learning", "ml ", "ai "],
    "marketing": ["marketing", "growth", "content", "seo", "social media", "communications"],
    "sales": ["sales", "account executive", "account manager", "business development", "bdr", "sdr", "revenue"],
    "operations": ["operations", "ops", "supply chain", "logistics"],
    "finance": ["finance", "accounting", "controller", "treasury", "fp&a"],
    "hr": ["recruiter", "recruiting", "people", "talent", "hr ", "human resources"],
    "legal": ["legal", "counsel", "compliance", "regulatory"],
    "security": ["security", "infosec", "cybersecurity", "appsec"],
    "support": ["support", "customer success", "customer experience", "helpdesk"],
}

# Remote type detection
REMOTE_PATTERNS = [
    (r"\b(fully\s+)?remote\b", "remote"),
    (r"\bhybrid\b", "hybrid"),
    (r"\bon[\s-]?site\b", "onsite"),
    (r"\bin[\s-]?office\b", "onsite"),
]


def detect_seniority(title: str) -> str:
    """Detect seniority level from job title. Returns lowercase."""
    title_lower = title.lower()
    for pattern, level in SENIORITY_PATTERNS:
        if re.search(pattern, title_lower):
            return level
    return "mid"  # default


def detect_department(title: str, department_hint: str = "") -> str:
    """Detect department from title and optional ATS department field."""
    # If ATS provides department, use it directly
    if department_hint:
        dept_lower = department_hint.lower()
        for dept, keywords in DEPARTMENT_MAP.items():
            for kw in keywords:
                if kw in dept_lower:
                    return dept.capitalize()
        return department_hint.strip().title()

    # Infer from title
    title_lower = title.lower()
    for dept, keywords in DEPARTMENT_MAP.items():
        for kw in keywords:
            if kw in title_lower:
                return dept.capitalize()
    return "Other"


def detect_remote_type(location: str, is_remote: bool | None = None, workplace_type: str = "") -> str:
    """Detect remote/hybrid/onsite from location string and ATS fields."""
    if workplace_type:
        wt = workplace_type.lower()
        if "remote" in wt:
            return "remote"
        if "hybrid" in wt:
            return "hybrid"
        if "onsite" in wt or "on-site" in wt:
            return "onsite"

    if is_remote is True:
        return "remote"

    if location:
        loc_lower = location.lower()
        for pattern, rtype in REMOTE_PATTERNS:
            if re.search(pattern, loc_lower):
                return rtype

    return "onsite"


def normalize_employment_type(raw: str) -> str:
    """Normalize employment type string."""
    if not raw:
        return "Full-time"
    r = raw.lower().strip()
    if "full" in r:
        return "Full-time"
    if "part" in r:
        return "Part-time"
    if "contract" in r:
        return "Contract"
    if "intern" in r:
        return "Internship"
    if "temp" in r:
        return "Temporary"
    return raw.strip().title()


# Salary patterns — match $120K, $120,000, 120k-150k, etc.
_SALARY_PATTERN = re.compile(
    r"\$?\s*(\d{2,3})[,.]?(\d{3})?\s*(?:k)?\s*(?:[-–—to]+)\s*\$?\s*(\d{2,3})[,.]?(\d{3})?\s*(?:k)?",
    re.IGNORECASE,
)
_SALARY_SINGLE = re.compile(
    r"\$\s*(\d{2,3})[,.]?(\d{3})?\s*(?:k)?",
    re.IGNORECASE,
)


def extract_salary(text: str) -> tuple[int | None, int | None]:
    """Extract salary range from text. Returns (min, max) in USD or (None, None)."""
    if not text:
        return None, None

    # Try range first: $120K - $150K or $120,000 - $150,000
    m = _SALARY_PATTERN.search(text)
    if m:
        low = _parse_salary_num(m.group(1), m.group(2))
        high = _parse_salary_num(m.group(3), m.group(4))
        if low and high and 30_000 <= low <= 1_000_000 and 30_000 <= high <= 1_000_000:
            return low, high

    # Single figure
    singles = _SALARY_SINGLE.findall(text)
    if singles:
        values = [_parse_salary_num(s[0], s[1]) for s in singles]
        values = [v for v in values if v and 30_000 <= v <= 1_000_000]
        if len(values) >= 2:
            return min(values), max(values)
        elif len(values) == 1:
            return values[0], values[0]

    return None, None


def _parse_salary_num(main: str, thousands: str | None) -> int | None:
    """Parse salary number from regex groups."""
    if not main:
        return None
    num = int(main)
    if thousands:
        num = num * 1000 + int(thousands)
    elif num < 1000:
        num *= 1000  # "120" → 120K
    return num


# ── Visa sponsorship detection ────────────────────────────────────────────

_VISA_POSITIVE = re.compile(
    r"visa\s+sponsor|sponsor.*visa|h-?1b\s+sponsor|immigration\s+sponsor|"
    r"will\s+sponsor|sponsorship\s+(?:is\s+)?available|provide\s+(?:visa\s+)?sponsorship|"
    r"open\s+to\s+sponsorship",
    re.IGNORECASE,
)
_VISA_NEGATIVE = re.compile(
    r"no\s+(?:visa\s+)?sponsor|not\s+(?:provide|offer).*sponsor|"
    r"unable\s+to\s+sponsor|cannot\s+sponsor|won'?t\s+sponsor|"
    r"do\s+not\s+sponsor|does\s+not\s+sponsor|without\s+sponsor|"
    r"sponsorship\s+(?:is\s+)?not\s+available|not\s+eligible\s+for\s+sponsorship",
    re.IGNORECASE,
)


def detect_visa_sponsorship(text: str) -> bool | None:
    """Detect visa sponsorship from job description.
    Returns True (sponsors), False (doesn't), or None (not mentioned).
    """
    if not text:
        return None
    # Check negative patterns first (more specific)
    if _VISA_NEGATIVE.search(text):
        return False
    if _VISA_POSITIVE.search(text):
        return True
    return None


def normalize_job_rules(
    title: str, location: str = "", description: str = "", ats_metadata: dict | None = None
) -> dict:
    """
    Rule-based normalization. No LLM needed.
    Returns the same metadata format as the LLM normalizer.
    """
    meta = ats_metadata or {}

    seniority = detect_seniority(title)
    department = detect_department(title, meta.get("department", "") or meta.get("team", ""))
    remote_type = detect_remote_type(
        location,
        is_remote=meta.get("is_remote"),
        workplace_type=meta.get("workplace_type", ""),
    )
    employment_type = normalize_employment_type(meta.get("employment_type", "") or meta.get("commitment", ""))

    skills = extract_skills_from_text(f"{title} {description[:3000]}")

    salary_min, salary_max = extract_salary(description[:2000])

    visa = detect_visa_sponsorship(description)

    result = {
        "canonical_title": title.strip(),
        "seniority_level": seniority,
        "department": department,
        "employment_type": employment_type,
        "remote_type": remote_type,
        "normalized_location": {"raw": location},
        "skills": skills,
        "experience_range": "",
    }

    # Also extract from ATS metadata compensation if available
    comp = meta.get("compensation", "") or meta.get("compensationTierSummary", "") or meta.get("salary", "")
    if comp and salary_min is None:
        salary_min, salary_max = extract_salary(str(comp))

    if salary_min is not None:
        result["salary_min"] = salary_min
    if salary_max is not None:
        result["salary_max"] = salary_max
    if visa is not None:
        result["visa_sponsorship"] = visa

    return result
