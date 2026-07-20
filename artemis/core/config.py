from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    model_config = {"env_prefix": "ARTEMIS_", "env_file": ".env", "extra": "ignore"}

    database_url: str = Field(
        default="postgresql+asyncpg://artemis:artemis@localhost:5432/artemis",
        description="Async PostgreSQL connection string",
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Azure OpenAI — primary endpoint
    azure_openai_api_key: str = Field(default="")
    azure_openai_endpoint: str = Field(default="")
    azure_openai_api_version: str = Field(default="2024-10-21")
    # Optional secondary endpoint (different region) for rate-limit failover + load balancing.
    # When both are configured, requests are round-robined; on 429 the client is marked
    # throttled and traffic shifts to the other endpoint until the cooldown expires.
    azure_openai_api_key_2: str = Field(default="")
    azure_openai_endpoint_2: str = Field(default="")
    llm_model: str = Field(default="gpt-4.1")
    embedding_model: str = Field(default="text-embedding-3-small")

    github_token: str = Field(default="")
    github_repo: str = Field(default="", description="owner/repo for PR creation")

    # Company discovery
    crunchbase_api_key: str = Field(default="", description="Crunchbase API v4 key")

    scrape_rate_limit: float = Field(default=1.5, description="Min seconds between requests to same domain")
    scrape_default_limit: int = Field(default=500, description="Default max jobs per scrape")
    configs_dir: str = Field(default="configs/companies", description="Path to company YAML configs")

    # Enrichment queue tuning
    enrich_batch_threshold: int = Field(default=10, description="Flush queue when this many jobs pending")
    enrich_flush_interval: int = Field(default=900, description="Force flush after this many seconds")

    # Connection pool
    db_pool_size: int = Field(default=20)
    db_max_overflow: int = Field(default=30)

    # Internal API
    internal_api_port: int = Field(default=8081, description="Port for internal API (called by Go)")

    # Monitor (job liveness checking)
    monitor_batch_size: int = Field(default=5000, description="Jobs per monitor cycle")
    monitor_concurrency_per_domain: int = Field(default=5, description="Max concurrent checks per ATS domain")
    monitor_interval_seconds: int = Field(default=120, description="Cron interval for monitor worker")
    monitor_max_consecutive_failures: int = Field(default=5, description="Mark stale after this many errors")

    # Webhook
    webhook_url: str = Field(default="", description="URL to POST job status changes to")
    webhook_secret: str = Field(default="", description="HMAC-SHA256 secret for webhook signing")

    # S3 / MinIO (resume storage)
    s3_endpoint: str = Field(default="http://localhost:9000", description="MinIO/S3 endpoint")
    s3_access_key: str = Field(default="artemis", description="S3 access key")
    s3_secret_key: str = Field(default="artemis123", description="S3 secret key")
    s3_bucket: str = Field(default="artemis-resumes", description="S3 bucket for resume files")
    s3_region: str = Field(default="us-east-1")

    # Recommendations
    recommendation_cache_ttl: int = Field(default=86400, description="Redis TTL for recommendations (24h)")


settings = Settings()
