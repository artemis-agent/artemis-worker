"""
User service — resume parsing, profile embedding, recommendations.

Consolidates resume/parser.py + recommend/engine.py into a clean service layer.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from io import BytesIO

import pdfplumber

from artemis.core.ai import get_ai_client
from artemis.core.config import settings
from artemis.core.database import async_session
from artemis.core.models import Resume, UserSkill
from artemis.core.prompts import PARSE_RESUME
from artemis.core.redis import get_redis
from artemis.normalizer.skill_taxonomy import normalize_skill, normalize_skills
from artemis.resume.storage import download_resume
from sqlalchemy import select

logger = logging.getLogger("artemis.services.user")


# ── Resume parsing ────────────────────────────────────────────────────────

async def extract_text_from_pdf(pdf_data: bytes) -> str:
    """Extract text from PDF using pdfplumber."""
    text_parts = []
    with pdfplumber.open(BytesIO(pdf_data)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


async def interpret_resume(raw_text: str) -> dict:
    """Use LLM to interpret extracted resume text into structured data."""
    client = get_ai_client()
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": "You are a resume parsing expert. Return only valid JSON."},
            {"role": "user", "content": PARSE_RESUME.format(resume_text=raw_text[:8000])},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


async def embed_user_profile(parsed_data: dict) -> list[float]:
    """Generate rich embedding for a user profile — mirrors job embedding space."""
    parts = []

    # Role identity
    role_parts = []
    if parsed_data.get("headline"):
        role_parts.append(parsed_data["headline"])
    if parsed_data.get("seniority_level"):
        role_parts.append(f"{parsed_data['seniority_level']} level")
    if parsed_data.get("desired_roles"):
        role_parts.append("seeking " + ", ".join(parsed_data["desired_roles"][:5]))
    if role_parts:
        parts.append(" ".join(role_parts))

    # Summary
    if parsed_data.get("summary"):
        parts.append(parsed_data["summary"][:300])

    # Skills (normalized)
    if parsed_data.get("skills"):
        skill_names = [s["name"] if isinstance(s, dict) else s for s in parsed_data["skills"]]
        normalized = normalize_skills(skill_names)
        parts.append("Skills: " + ", ".join(normalized[:25]))

    # Experience signals
    if parsed_data.get("experience"):
        exp = parsed_data["experience"]
        recent = exp[:3]  # most recent positions
        for e in recent:
            title = e.get("title", "")
            company = e.get("company", "")
            techs = e.get("technologies", [])
            exp_line = f"{title} at {company}" if company else title
            if techs:
                exp_line += f" ({', '.join(techs[:5])})"
            if exp_line:
                parts.append(exp_line)

    if parsed_data.get("years_of_experience"):
        parts.append(f"{parsed_data['years_of_experience']} years experience")

    # Location preferences
    if parsed_data.get("preferred_locations"):
        parts.append(", ".join(parsed_data["preferred_locations"][:5]))

    text = " | ".join(parts) if parts else "general professional"

    client = get_ai_client()
    response = await client.embeddings.create(model=settings.embedding_model, input=[text])
    return response.data[0].embedding


async def _set_parse_progress(resume_id: str, stage: str, pct: int):
    """Store parse progress in Redis for frontend polling."""
    try:
        rdb = await get_redis()
        await rdb.setex(f"artemis:parse_progress:{resume_id}", 300, json.dumps({"stage": stage, "percent": pct}))
    except Exception:
        pass


async def get_parse_progress(resume_id: str) -> dict | None:
    """Get current parse progress from Redis."""
    try:
        rdb = await get_redis()
        data = await rdb.get(f"artemis:parse_progress:{resume_id}")
        return json.loads(data) if data else None
    except Exception:
        return None


async def parse_and_store_resume(user_id: str, resume_id: str, s3_key: str) -> dict:
    """Full resume pipeline: download → extract → interpret → store."""
    await _set_parse_progress(resume_id, "Downloading resume...", 10)
    pdf_data = await download_resume(s3_key)

    await _set_parse_progress(resume_id, "Extracting text from PDF...", 25)
    raw_text = await extract_text_from_pdf(pdf_data)
    if not raw_text.strip():
        raise ValueError("Could not extract text from PDF")

    await _set_parse_progress(resume_id, "AI is analyzing your experience...", 40)
    parsed_data = await interpret_resume(raw_text)

    await _set_parse_progress(resume_id, "Saving your profile...", 80)

    async with async_session() as session:
        resume = await session.get(Resume, uuid.UUID(resume_id))
        if not resume:
            raise ValueError(f"Resume {resume_id} not found")

        resume.raw_text = raw_text
        resume.parsed_data = parsed_data
        resume.parsed_at = datetime.now(timezone.utc)

        skills = parsed_data.get("skills", [])
        skill_names_raw = [s["name"] if isinstance(s, dict) else s for s in skills]
        skill_names = normalize_skills(skill_names_raw)
        for name in skill_names:
            session.add(UserSkill(user_id=uuid.UUID(user_id), skill=name, source="resume"))

        # Update user profile directly from parsed data
        from artemis.core.models import User
        user = await session.get(User, uuid.UUID(user_id))
        if user:
            user.profile = {
                "experience": parsed_data.get("experience", []),
                "education": parsed_data.get("education", []),
                "certifications": parsed_data.get("certifications", []),
                "projects": parsed_data.get("projects", []),
                "languages": parsed_data.get("languages", []),
                "contact": parsed_data.get("contact", {}),
            }
            if parsed_data.get("headline"):
                user.headline = parsed_data["headline"]
            if parsed_data.get("summary"):
                user.summary = parsed_data["summary"]
            if parsed_data.get("seniority_level"):
                user.seniority_level = parsed_data["seniority_level"]
            if parsed_data.get("years_of_experience"):
                user.years_experience = parsed_data["years_of_experience"]
            if parsed_data.get("preferred_locations"):
                user.location = parsed_data["preferred_locations"][0]
            if parsed_data.get("desired_roles"):
                user.desired_roles = parsed_data["desired_roles"]

        await session.commit()

    await invalidate_recommendation_cache(user_id)

    await _set_parse_progress(resume_id, "Done!", 100)

    # Fire-and-forget: generate embedding async (don't block the response)
    import asyncio
    asyncio.create_task(_embed_and_store(resume_id, parsed_data))

    return {
        "resume_id": resume_id,
        "skills_count": len(skills),
        "parsed_data": parsed_data,
    }


async def _embed_and_store(resume_id: str, parsed_data: dict):
    """Background task: generate embedding and store it on the resume."""
    try:
        embedding = await embed_user_profile(parsed_data)
        async with async_session() as session:
            resume = await session.get(Resume, uuid.UUID(resume_id))
            if resume:
                resume.embedding = embedding
                await session.commit()
        logger.info(f"embedding stored for resume {resume_id} ({len(embedding)}d)")
    except Exception as e:
        logger.error(f"embedding failed for resume {resume_id}: {e}")


# ── Recommendations ───────────────────────────────────────────────────────

CACHE_PREFIX = "artemis:recommend:"


async def get_recommendations(user_id: str, limit: int = 20, skip_cache: bool = False) -> list[dict]:
    """Get job recommendations for a user. Uses Redis cache (24h TTL)."""
    cache_key = f"{CACHE_PREFIX}{user_id}"

    if not skip_cache:
        rdb = await get_redis()
        cached = await rdb.get(cache_key)
        if cached:
            logger.info(f"recommendations cache hit for user {user_id}")
            return json.loads(cached)[:limit]

    recs = await _compute_recommendations(user_id, limit)

    rdb = await get_redis()
    await rdb.setex(cache_key, settings.recommendation_cache_ttl, json.dumps(recs, default=str))
    return recs


async def invalidate_recommendation_cache(user_id: str):
    """Invalidate cached recommendations after profile/resume change."""
    rdb = await get_redis()
    await rdb.delete(f"{CACHE_PREFIX}{user_id}")


async def _compute_recommendations(user_id: str, limit: int = 20) -> list[dict]:
    """Compute recommendations using multi-factor scoring:

    1. Vector similarity (semantic match between profile & job embeddings)
    2. Skill overlap (taxonomy-normalized intersection)
    3. Skill category match (same domains even if different specific skills)
    4. Location match (preferred locations, remote friendliness)
    5. Seniority match (exact or adjacent levels)
    6. Desired role match (title alignment with user's desired roles)
    7. Recency boost (newer postings ranked slightly higher)
    """
    from artemis.core.models import Job, User
    from artemis.normalizer.skill_taxonomy import normalize_skill, get_skill_category
    from sqlalchemy import text
    from datetime import datetime, timezone, timedelta

    async with async_session() as session:
        # Get user's latest resume embedding
        result = await session.execute(
            select(Resume)
            .where(Resume.user_id == user_id)
            .where(Resume.embedding.isnot(None))
            .order_by(Resume.uploaded_at.desc())
            .limit(1)
        )
        resume = result.scalar_one_or_none()
        if not resume:
            return []

        # Get user's skills (normalized via taxonomy)
        skills_result = await session.execute(
            select(UserSkill.skill).where(UserSkill.user_id == user_id)
        )
        user_skills = {normalize_skill(row.skill).lower() for row in skills_result.all()}
        user_skill_categories = {get_skill_category(s) for s in user_skills} - {"other"}

        # Get user profile data
        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        user_location = (user.location or "").lower() if user else ""
        parsed = resume.parsed_data or {}
        preferred_locations = [loc.lower() for loc in parsed.get("preferred_locations", [])]
        seniority = (parsed.get("seniority_level") or (user.seniority_level if user else "") or "").lower()
        desired_roles = [r.lower() for r in (parsed.get("desired_roles") or (user.desired_roles if user else []) or [])]

        # Fetch candidates via vector similarity — wider net for better re-ranking
        # Note: CAST(... AS vector) is used instead of :embedding::vector because
        # the `::` cast syntax conflicts with SQLAlchemy named-param syntax.
        q = text("""
            SELECT j.id, j.title, j.url, j.location, j.metadata, j.date_posted,
                   j.source, j.created_at,
                   c.name AS company_name, c.slug AS company_slug,
                   1 - (j.embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM jobs j
            JOIN companies c ON j.company_id = c.id
            WHERE j.embedding IS NOT NULL AND j.is_active = true
            ORDER BY j.embedding <=> CAST(:embedding AS vector)
            LIMIT :candidate_limit
        """)
        rows = await session.execute(q, {
            "embedding": str(resume.embedding.tolist()),
            "candidate_limit": limit * 10,
        })
        candidates = rows.mappings().all()

    # Seniority adjacency map — adjacent levels get partial credit
    SENIORITY_ORDER = ["intern", "junior", "mid", "senior", "staff", "principal", "director", "vp", "c-level"]
    seniority_idx = {s: i for i, s in enumerate(SENIORITY_ORDER)}

    def seniority_score(job_seniority: str) -> float:
        if not seniority or not job_seniority:
            return 0.3  # neutral if unknown
        user_idx = seniority_idx.get(seniority, -1)
        job_idx = seniority_idx.get(job_seniority.lower(), -1)
        if user_idx == -1 or job_idx == -1:
            return 0.3
        diff = abs(user_idx - job_idx)
        if diff == 0:
            return 1.0
        if diff == 1:
            return 0.6
        return 0.0

    now = datetime.now(timezone.utc)

    scored = []
    for c in candidates:
        vector_sim = float(c["similarity"])
        meta = c["metadata"] or {}

        # ── Skill overlap (taxonomy-normalized) ──
        job_skills_raw = meta.get("skills", [])
        job_skills = {normalize_skill(s).lower() for s in job_skills_raw}
        skill_intersection = user_skills & job_skills
        skill_overlap = len(skill_intersection) / max(len(user_skills | job_skills), 1)

        # ── Skill category overlap (domain match) ──
        job_categories = {get_skill_category(s) for s in job_skills} - {"other"}
        category_overlap = len(user_skill_categories & job_categories) / max(len(user_skill_categories | job_categories), 1) if user_skill_categories else 0

        # ── Location match ──
        job_loc = (c["location"] or "").lower()
        remote_type = (meta.get("remote_type") or "").lower()
        loc_score = 0.0
        if user_location and user_location in job_loc:
            loc_score = 1.0
        elif any(pl in job_loc for pl in preferred_locations if pl):
            loc_score = 0.8
        elif "remote" in job_loc or "remote" in remote_type:
            loc_score = 0.6

        # ── Seniority match ──
        sen_score = seniority_score(meta.get("seniority_level", ""))

        # ── Desired role match (title similarity) ──
        job_title_lower = (c["title"] or "").lower()
        role_score = 0.0
        if desired_roles:
            for dr in desired_roles:
                dr_words = dr.split()
                if any(w in job_title_lower for w in dr_words if len(w) > 3):
                    role_score = max(role_score, 0.7)
                if dr in job_title_lower:
                    role_score = 1.0
                    break

        # ── Recency boost ──
        posted = c["date_posted"] or c["created_at"]
        if posted:
            if hasattr(posted, 'tzinfo') and posted.tzinfo is None:
                posted = posted.replace(tzinfo=timezone.utc)
            days_old = max((now - posted).days, 0)
            recency = max(1.0 - (days_old / 60), 0.0)  # linear decay over 60 days
        else:
            recency = 0.3

        # ── Final weighted score ──
        score = (
            0.35 * vector_sim +
            0.20 * skill_overlap +
            0.10 * category_overlap +
            0.10 * loc_score +
            0.10 * sen_score +
            0.10 * role_score +
            0.05 * recency
        )

        scored.append({
            "job_id": str(c["id"]),
            "title": c["title"],
            "url": c["url"],
            "location": c["location"],
            "company_name": c["company_name"],
            "company_slug": c["company_slug"],
            "source": c["source"],
            "score": round(score, 4),
            "signals": {
                "vector_similarity": round(vector_sim, 4),
                "skill_overlap": round(skill_overlap, 4),
                "category_match": round(category_overlap, 4),
                "location_match": round(loc_score, 2),
                "seniority_match": round(sen_score, 2),
                "role_match": round(role_score, 2),
                "recency": round(recency, 2),
            },
            "matched_skills": sorted(skill_intersection)[:10],
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]
