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


JUDGE_PROFILE = """You are a senior tech recruiter building a LinkedIn-style profile from raw resume data. Be brutally honest — no inflation, no flattery.

Your job: take this raw parsed resume and construct a COMPLETE professional profile. Write it like a recruiter who's seen 10,000 profiles and knows exactly what makes one stand out vs. blend in.

Raw resume data:
---
{resume_json}
---

Build the full profile. Return ONLY a JSON object:
{{
  "name": "Their actual name",
  "headline": "Write a killer LinkedIn headline. Format: 'Role | Core Skills | Domain'. Be specific, not generic. If they're a junior pretending to be senior, the headline should reflect reality.",
  "summary": "Write a 3-4 sentence professional summary in FIRST PERSON. What they actually do, what they're good at, what they bring to the table. Be honest — if their experience is thin, don't oversell it. If they're genuinely strong, make it punch.",
  "seniority_level": "intern | junior | mid | senior | staff | principal | director | vp | c-level — based on ACTUAL experience duration and role progression, NOT what they claim",
  "years_of_experience": 5,
  "location": "Primary work location",
  "skills": [
    {{"name": "Python", "proficiency": "advanced", "years": 4, "verdict": "Legitimate — used across multiple production roles"}},
    {{"name": "Kubernetes", "proficiency": "beginner", "years": 0, "verdict": "Listed but no evidence of real usage. Probably did a tutorial."}}
  ],
  "experience": [
    {{
      "title": "Clean title — standardize to industry norms",
      "company": "Company Name",
      "location": "City, Country",
      "start_date": "2022-01",
      "end_date": "2024-06",
      "is_current": false,
      "impact": "1-2 sentences about what they ACTUALLY delivered. Strip the buzzwords. 'Built X that did Y' not 'Leveraged synergies to drive outcomes'.",
      "technologies": ["Python", "FastAPI", "PostgreSQL"]
    }}
  ],
  "education": [
    {{"degree": "B.S. Computer Science", "institution": "MIT", "year": 2022, "relevance": "Directly relevant" }}
  ],
  "certifications": [
    {{"name": "AWS Solutions Architect", "issuer": "Amazon", "year": 2023, "value": "Industry-recognized, adds credibility"}}
  ],
  "languages": ["English", "Hindi"],
  "desired_roles": ["Roles they'd actually be competitive for based on their background — not aspirational fantasy roles"],
  "preferred_locations": ["Where they've worked or could realistically work"],
  "profile_score": 72,
  "profile_verdict": "3-4 sentences. Be the honest friend. 'You have solid backend chops with 4 years of Python but your cloud skills are surface-level. Stop listing Kubernetes if you've only used minikube. Your Stripe experience is your strongest card — lead with it.' ",
  "strengths": ["Specific strength backed by evidence from resume"],
  "gaps": ["Specific gap — name the skill or experience they're missing"],
  "career_advice": ["One actionable thing they should do to level up"]
}}

Rules:
- proficiency levels: beginner (0-1y, tutorials), intermediate (1-3y, used in work), advanced (3-5y, deep expertise), expert (5y+, taught others/led architecture)
- seniority: Count ACTUAL years of relevant work. 2 years = junior. 4-6 = mid. 7+ = senior. Staff/principal needs demonstrated tech leadership.
- If someone lists 15 skills but their resume shows 2 projects, call it out. Skill spam is a red flag.
- If their education is from a top school, it matters. If it's irrelevant to their career, say so.
- desired_roles should be REALISTIC — if a 2-year dev wants to be a Staff Engineer, that's not a desired role, it's a 5-year goal.
- Return ONLY valid JSON"""
