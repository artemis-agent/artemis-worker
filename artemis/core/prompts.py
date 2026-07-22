"""Centralized LLM prompts — single source of truth."""

EXTRACT_ATS_FROM_SEARCH = """You are an ATS-detection assistant. Given web search results for a company's careers page, identify which Applicant Tracking System (ATS) the company uses and the slug/tenant needed to query it.

Company: {company_name}

Search results (top 10):
{results}

Supported ATS systems and the EXACT config keys we need (use these names literally):
- greenhouse: {{"board_token": "<slug>"}}                                    e.g. "stripe" from boards.greenhouse.io/stripe
- lever: {{"company": "<slug>"}}                                             e.g. "netflix" from jobs.lever.co/netflix
- ashby: {{"board_token": "<slug>"}}                                         e.g. "linear" from jobs.ashbyhq.com/linear
- workday: {{"tenant": "<sub>", "site_id": "<site>", "wd_version": "5"}}     e.g. tenant="disney", site_id="DisneyCareers" from disney.wd5.myworkdayjobs.com/en-US/DisneyCareers
- smartrecruiters: {{"company_id": "<Slug>"}}                                e.g. "Bosch" from jobs.smartrecruiters.com/Bosch (case-sensitive)
- eightfold: {{"company": "<slug>", "domain": "<host>.com"}}                 e.g. company="microsoft", domain="microsoft.com" from microsoft.eightfold.ai
- icims: {{"careers_url": "https://<sub>.icims.com/jobs/search"}}            e.g. "careers-acme" subdomain

Respond ONLY with strict JSON:
{{
  "ats": "<one of greenhouse|lever|ashby|workday|smartrecruiters|eightfold|icims|unknown>",
  "config": {{ ... ats-specific fields ... }},
  "confidence": <0.0-1.0>,
  "evidence_url": "<the search-result URL that proves this>"
}}

Return ats="unknown" if none of the results point to one of the 7 supported systems.
"""


VERIFY_COMPANY_MATCH = """You are verifying that an ATS board belongs to the requested company (not a name collision).

Requested company: {company_name}
ATS hit: {ats} board "{slug}" with {job_count} open jobs
Sample job titles from the board:
{titles}

Question: Do these jobs plausibly belong to "{company_name}"?

Consider: industry alignment, the company's actual product/service, brand cues in titles or locations. A small generic board with no clear connection is likely a false positive (e.g. "eli" board with 4 generic IT roles is NOT Eli Lilly).

Respond ONLY with strict JSON: {{"is_match": <true|false>, "reason": "<one short sentence>"}}"""


NORMALIZE_JOB = """You are a job posting normalizer. Given raw job data, extract structured metadata.

For each job, return:
- canonical_title: Clean, standardized title (e.g., "Software Engineer" not "SWE III")
- seniority_level: One of: intern, junior, mid, senior, staff, principal, director, vp, c-level
- department: Engineering, Product, Design, Marketing, Sales, Operations, Finance, HR, Legal, Data, Security, DevOps, Other
- experience_range: e.g., "0-1 years", "3-5 years", "7+ years". Infer from title/description if not explicit.
- skills: List of technical skills, frameworks, languages mentioned (max 15)
- normalized_location: {city, state, country, remote_type} where remote_type is one of: onsite, remote, hybrid, unknown

Respond ONLY with a JSON array of objects matching the count and order of input jobs."""


PARSE_RESUME = """You are a ruthlessly precise resume parser. Extract every useful signal from this resume.

Resume text:
---
{resume_text}
---

Return a JSON object with these fields:
{{
  "name": "Full Name",
  "headline": "One-line professional identity (e.g. 'Senior Backend Engineer | Go, Python, Distributed Systems')",
  "summary": "2-3 sentence professional summary — what they actually DO, not what they WANT",
  "seniority_level": "mid",
  "years_of_experience": 5,
  "skills": [
    {{"name": "Python", "proficiency": "advanced", "years": 4}},
    {{"name": "AWS", "proficiency": "intermediate", "years": 2}}
  ],
  "experience": [
    {{
      "title": "Software Engineer",
      "company": "Acme Corp",
      "location": "San Francisco, US",
      "start_date": "2022-01",
      "end_date": "2024-06",
      "is_current": false,
      "description": "What they actually built/shipped — be specific",
      "technologies": ["Python", "FastAPI", "PostgreSQL"]
    }}
  ],
  "education": [
    {{
      "degree": "B.S. Computer Science",
      "institution": "MIT",
      "location": "Cambridge, US",
      "year": 2022,
      "gpa": "3.8/4.0"
    }}
  ],
  "certifications": [
    {{"name": "AWS Solutions Architect", "issuer": "Amazon", "year": 2023}}
  ],
  "projects": [
    {{"name": "Project Name", "description": "What it does", "technologies": ["React", "Node.js"], "url": ""}}
  ],
  "languages": ["English", "Hindi"],
  "preferred_locations": ["San Francisco, US", "Remote"],
  "desired_roles": ["Backend Engineer", "Platform Engineer"],
  "contact": {{
    "email": "",
    "linkedin": "",
    "github": "",
    "website": ""
  }}
}}

Rules:
- seniority_level: intern | junior | mid | senior | staff | principal | director | vp | c-level
- proficiency: beginner | intermediate | advanced | expert
- Infer preferred_locations from work history and stated preferences
- Calculate years_of_experience from total work duration, not what they claim
- If info is missing, omit the field — do NOT fabricate
- Return ONLY valid JSON"""
