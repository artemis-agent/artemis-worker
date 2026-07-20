import enum
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Boolean,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class ATSType(str, enum.Enum):
    workday = "workday"
    greenhouse = "greenhouse"
    lever = "lever"
    ashby = "ashby"
    eightfold = "eightfold"
    icims = "icims"
    smartrecruiters = "smartrecruiters"
    taleo = "taleo"
    custom = "custom"


class CompanyStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    pending = "pending"


class ScrapeRunStatus(str, enum.Enum):
    running = "running"
    success = "success"
    failed = "failed"


class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    ats_type = Column(Enum(ATSType), nullable=False)
    careers_url = Column(Text, nullable=False)
    ats_config = Column(JSONB, nullable=False, default=dict)
    status = Column(Enum(CompanyStatus), nullable=False, default=CompanyStatus.active)
    last_scraped_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    crunchbase_permalink = Column(String(255), unique=True, nullable=True, index=True)
    crunchbase_uuid = Column(UUID(as_uuid=True), unique=True, nullable=True)
    crunchbase_image_id = Column(Text, nullable=True)  # kept raw so logo URL can be regenerated
    # Existing display columns shared with the Go API (artemis-api).
    website = Column(Text, nullable=True)
    logo_url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    # CB-specific social URLs.
    linkedin_url = Column(Text, nullable=True)
    twitter_url = Column(Text, nullable=True)
    facebook_url = Column(Text, nullable=True)
    crunchbase_synced_at = Column(DateTime(timezone=True), nullable=True)

    jobs = relationship("Job", back_populates="company", lazy="selectin")
    scrape_runs = relationship("ScrapeRun", back_populates="company", lazy="selectin")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String(512), nullable=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(512), nullable=False)
    url = Column(Text, unique=True, nullable=False)
    location = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    date_posted = Column(DateTime(timezone=True), nullable=True)
    source = Column(String(128), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # Normalization metadata (Workflow 1)
    metadata_ = Column("metadata", JSONB, nullable=True)
    normalized_at = Column(DateTime(timezone=True), nullable=True)

    # Salary (extracted from description / ATS metadata)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_currency = Column(String(8), nullable=True, default="USD")
    short_summary = Column(Text, nullable=True)
    visa_sponsorship = Column(Boolean, nullable=True)

    # Embedding vector (Workflow 2)
    embedding = Column(Vector(1536), nullable=True)
    embedded_at = Column(DateTime(timezone=True), nullable=True)

    # Monitor (liveness checking)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    check_status = Column(String(32), nullable=True)  # ok, inactive, changed, error, stale
    consecutive_check_failures = Column(Integer, nullable=False, default=0)

    first_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    company = relationship("Company", back_populates="jobs")

    __table_args__ = (
        Index("ix_jobs_company_id", "company_id"),
        Index("ix_jobs_is_active", "is_active"),
        Index("ix_jobs_metadata", "metadata", postgresql_using="gin"),
        Index("ix_jobs_check_schedule", "last_checked_at", postgresql_where=text("is_active = true")),
    )


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(ScrapeRunStatus), nullable=False, default=ScrapeRunStatus.running)
    jobs_found = Column(Integer, nullable=False, default=0)
    jobs_new = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    company = relationship("Company", back_populates="scrape_runs")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(Text, nullable=False, default="")
    headline = Column(Text, nullable=True, default="")
    summary = Column(Text, nullable=True, default="")
    profile_photo_url = Column(Text, nullable=True, default="")
    location = Column(Text, nullable=True)
    seniority_level = Column(String(64), nullable=True, default="")
    years_experience = Column(Integer, nullable=True, default=0)
    desired_roles = Column(JSONB, nullable=True, default=list)
    onboarding_completed = Column(Boolean, nullable=False, default=False)
    profile = Column(JSONB, nullable=True, default=dict)
    profile_score = Column(Integer, nullable=True, default=0)
    profile_assessment = Column(Text, nullable=True, default="")
    preferences = Column(JSONB, nullable=True, default=dict)
    embedding = Column(Vector(1536), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    resumes = relationship("Resume", back_populates="user", lazy="selectin")
    skills = relationship("UserSkill", back_populates="user", lazy="selectin")


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    s3_key = Column(Text, nullable=False)
    filename = Column(String(512), nullable=False)
    raw_text = Column(Text, nullable=True)
    parsed_data = Column(JSONB, nullable=True)
    embedding = Column(Vector(1536), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    parsed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="resumes")

    __table_args__ = (Index("ix_resumes_user_id", "user_id"),)


class UserSkill(Base):
    __tablename__ = "user_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    skill = Column(String(255), nullable=False)
    experience_years = Column(Integer, nullable=True)
    source = Column(String(64), nullable=False, default="resume")  # resume | manual

    user = relationship("User", back_populates="skills")

    __table_args__ = (Index("ix_user_skills_user_id", "user_id"),)
