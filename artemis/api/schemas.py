"""Pydantic schemas for internal API request/response validation."""

from pydantic import BaseModel


# ── Jobs / Scrape ──


class ScrapeRequest(BaseModel):
    company_id: str
    query: str = ""
    limit: int = 50


class ScrapeResponse(BaseModel):
    status: str
    job_id: str
    company_id: str


class EmbedRequest(BaseModel):
    text: str


class EmbedResponse(BaseModel):
    embedding: list[float]


# ── Resume ──


class ResumeParseRequest(BaseModel):
    user_id: str
    resume_id: str
    s3_key: str


class ResumeParseResponse(BaseModel):
    status: str
    resume_id: str
    skills_count: int = 0


# ── Recommendations ──


class RecommendRequest(BaseModel):
    user_id: str
    limit: int = 20
    skip_cache: bool = False


class RecommendResponse(BaseModel):
    recommendations: list[dict]
    total: int
    cached: bool = False


# ── User Profile Embedding ──


class UserEmbedRequest(BaseModel):
    user_id: str


class UserEmbedResponse(BaseModel):
    status: str
    dimensions: int = 0
