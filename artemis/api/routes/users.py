"""User-related internal API routes: resume parse, recommend, user embed."""

import logging
import uuid

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


logger = logging.getLogger("artemis.api.users")


async def parse_resume(request: Request) -> JSONResponse:
    """Parse a resume PDF from MinIO. Called by Go API after upload."""
    body = await request.json()
    user_id = body.get("user_id")
    resume_id = body.get("resume_id")
    s3_key = body.get("s3_key")

    if not all([user_id, resume_id, s3_key]):
        return JSONResponse({"error": "user_id, resume_id, s3_key required"}, status_code=400)

    from artemis.workers.enrich import resume_parse_task

    result = resume_parse_task.apply_async(args=[user_id, resume_id, s3_key], queue="enrich")

    return JSONResponse(
        {
            "status": "queued",
            "job_id": result.id,
            "resume_id": resume_id,
        }
    )


async def parse_progress(request: Request) -> JSONResponse:
    """Get resume parse progress."""
    resume_id = request.query_params.get("resume_id", "")
    if not resume_id:
        return JSONResponse({"error": "resume_id required"}, status_code=400)

    from artemis.services.user import get_parse_progress

    progress = await get_parse_progress(resume_id)
    if not progress:
        return JSONResponse({"stage": "Waiting...", "percent": 0})
    return JSONResponse(progress)


async def recommend_jobs(request: Request) -> JSONResponse:
    """Get job recommendations for a user."""
    body = await request.json()
    user_id = body.get("user_id")
    limit = body.get("limit", 20)
    skip_cache = body.get("skip_cache", False)

    if not user_id:
        return JSONResponse({"error": "user_id required"}, status_code=400)

    from artemis.services.user import get_recommendations

    recs = await get_recommendations(user_id, limit=limit, skip_cache=skip_cache)

    return JSONResponse(
        {
            "recommendations": recs,
            "total": len(recs),
            "cached": not skip_cache,
        }
    )


async def embed_user(request: Request) -> JSONResponse:
    """Generate/refresh embedding for a user profile.

    Builds the embedding from User table data (profile, skills, headline, summary)
    plus the latest resume parsed_data if available. Stores on the latest Resume row;
    if no resume exists yet, creates a synthetic placeholder Resume row to hold it.
    """
    body = await request.json()
    user_id = body.get("user_id")

    if not user_id:
        return JSONResponse({"error": "user_id required"}, status_code=400)

    from artemis.core.database import async_session
    from artemis.core.models import Resume, User, UserSkill
    from artemis.services.user import embed_user_profile, invalidate_recommendation_cache
    from sqlalchemy import select

    async with async_session() as session:
        uid = uuid.UUID(user_id)

        # Load user record
        user_res = await session.execute(select(User).where(User.id == uid))
        user = user_res.scalar_one_or_none()
        if not user:
            return JSONResponse({"error": "user not found"}, status_code=404)

        # Load latest resume (may be None if user hasn't uploaded one)
        resume_res = await session.execute(
            select(Resume).where(Resume.user_id == uid).order_by(Resume.uploaded_at.desc()).limit(1)
        )
        resume = resume_res.scalar_one_or_none()

        # Load skills from user_skills table
        skills_res = await session.execute(select(UserSkill.skill).where(UserSkill.user_id == uid))
        user_skills = [r.skill for r in skills_res.all()]

        # Build merged profile dict — resume data first, then overlay user table fields
        merged: dict = {}
        if resume and resume.parsed_data:
            merged.update(resume.parsed_data)

        # User table fields take precedence (most recent edits)
        if user.headline:
            merged["headline"] = user.headline
        if user.summary:
            merged["summary"] = user.summary
        if user.seniority_level:
            merged["seniority_level"] = user.seniority_level
        if user.years_experience:
            merged["years_of_experience"] = user.years_experience
        if user.desired_roles:
            merged["desired_roles"] = user.desired_roles
        if user.location:
            merged.setdefault("preferred_locations", [user.location])

        # Profile JSONB (experience, education, projects, certifications, languages)
        if user.profile and isinstance(user.profile, dict):
            for key in ("experience", "education", "certifications", "projects", "languages"):
                if user.profile.get(key):
                    merged[key] = user.profile[key]

        # Merge skills: resume parsed + user_skills (deduped)
        existing_skill_names = set()
        existing_skills = merged.get("skills", [])
        for s in existing_skills:
            name = s["name"] if isinstance(s, dict) else s
            existing_skill_names.add(name.lower())
        for sk in user_skills:
            if sk.lower() not in existing_skill_names:
                existing_skills.append(sk)
                existing_skill_names.add(sk.lower())
        if existing_skills:
            merged["skills"] = existing_skills

        if not merged:
            return JSONResponse({"error": "no profile data to embed"}, status_code=400)

        embedding = await embed_user_profile(merged)

        # Store on resume if exists; otherwise create a placeholder
        if resume:
            resume.embedding = embedding
        else:
            placeholder = Resume(
                id=uuid.uuid4(),
                user_id=uid,
                s3_key="",
                filename="profile-only",
                parsed_data=merged,
                embedding=embedding,
            )
            session.add(placeholder)

        await session.commit()

    # Invalidate cached recommendations so they're recomputed with new embedding
    await invalidate_recommendation_cache(user_id)

    return JSONResponse({"status": "embedded", "dimensions": len(embedding)})


routes = [
    Route("/internal/resume/parse", parse_resume, methods=["POST"]),
    Route("/internal/resume/progress", parse_progress, methods=["GET"]),
    Route("/internal/recommend", recommend_jobs, methods=["POST"]),
    Route("/internal/user/embed", embed_user, methods=["POST"]),
]
