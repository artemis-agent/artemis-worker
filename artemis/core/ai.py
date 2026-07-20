"""Multi-endpoint Azure OpenAI client pool.

Supports 1-N Azure OpenAI endpoints (typically in different regions) for:
- Load balancing via round-robin
- Automatic rate-limit failover: on 429 the endpoint is marked throttled and
  traffic shifts to other endpoints until the cooldown expires.

The pool is a drop-in for AsyncAzureOpenAI — exposes .chat.completions.create
and .embeddings.create with the same signatures.

Configure additional endpoints via env vars:
  ARTEMIS_AZURE_OPENAI_API_KEY        (primary)
  ARTEMIS_AZURE_OPENAI_ENDPOINT       (primary)
  ARTEMIS_AZURE_OPENAI_API_KEY_2      (optional secondary)
  ARTEMIS_AZURE_OPENAI_ENDPOINT_2     (optional secondary)
"""

import asyncio
import logging
import time

from openai import AsyncAzureOpenAI, RateLimitError

from artemis.core.config import settings

logger = logging.getLogger("artemis.core.ai")


class _Endpoint:
    """Wraps a single Azure OpenAI client with throttle-state tracking."""

    __slots__ = ("name", "client", "throttled_until")

    def __init__(self, name: str, client: AsyncAzureOpenAI):
        self.name = name
        self.client = client
        self.throttled_until = 0.0

    def is_available(self, now: float) -> bool:
        return self.throttled_until <= now

    def mark_throttled(self, retry_after: float):
        self.throttled_until = time.time() + max(retry_after, 1.0)


class AIClientPool:
    """Round-robin client pool with rate-limit failover."""

    def __init__(self, endpoints: list[_Endpoint]):
        if not endpoints:
            raise ValueError("AIClientPool requires at least one endpoint")
        self.endpoints = endpoints
        self._next_idx = 0
        # Sub-proxies that look like client.chat / client.embeddings
        self.chat = _ChatNamespace(self)
        self.embeddings = _EmbeddingsNamespace(self)

    def _pick_endpoint(self) -> _Endpoint:
        """Round-robin pick, skipping throttled endpoints when possible."""
        now = time.time()
        n = len(self.endpoints)
        for offset in range(n):
            idx = (self._next_idx + offset) % n
            ep = self.endpoints[idx]
            if ep.is_available(now):
                self._next_idx = (idx + 1) % n
                return ep
        # All throttled — return the one that recovers soonest
        return min(self.endpoints, key=lambda e: e.throttled_until)

    async def _call_with_failover(self, op_name: str, fn_name: str, **kwargs):
        """Try each endpoint until one succeeds or all are exhausted."""
        # Try up to 2*N times so we can come back to a recovered endpoint
        max_attempts = max(len(self.endpoints) * 2, 2)
        last_err: Exception | None = None

        for attempt in range(max_attempts):
            ep = self._pick_endpoint()
            now = time.time()

            # If this endpoint is throttled, wait until it recovers
            # (only happens when ALL endpoints are throttled)
            if not ep.is_available(now):
                wait = ep.throttled_until - now
                if wait > 0:
                    logger.warning(
                        f"all endpoints throttled; waiting {wait:.1f}s on {ep.name}"
                    )
                    await asyncio.sleep(min(wait, 60))

            try:
                # Look up the actual SDK method:
                # self.client.chat.completions.create or self.client.embeddings.create
                target = ep.client
                for attr in fn_name.split("."):
                    target = getattr(target, attr)
                return await target(**kwargs)
            except RateLimitError as e:
                retry_after = _parse_retry_after(e)
                ep.mark_throttled(retry_after)
                logger.warning(
                    f"{op_name}: 429 on {ep.name}, throttled for {retry_after:.0f}s "
                    f"(attempt {attempt + 1}/{max_attempts})"
                )
                last_err = e
                continue
            except Exception as e:
                # Non-rate-limit error — don't mark throttled, but try next endpoint once
                logger.warning(f"{op_name}: error on {ep.name}: {e}")
                last_err = e
                if attempt < max_attempts - 1:
                    continue
                raise

        if last_err:
            raise last_err
        raise RuntimeError(f"{op_name}: all endpoints exhausted")


class _ChatNamespace:
    """Mimics client.chat — exposes .completions.create()."""

    def __init__(self, pool: AIClientPool):
        self.completions = _ChatCompletions(pool)


class _ChatCompletions:
    def __init__(self, pool: AIClientPool):
        self._pool = pool

    async def create(self, **kwargs):
        return await self._pool._call_with_failover(
            "chat.completions", "chat.completions.create", **kwargs
        )


class _EmbeddingsNamespace:
    """Mimics client.embeddings — exposes .create()."""

    def __init__(self, pool: AIClientPool):
        self._pool = pool

    async def create(self, **kwargs):
        return await self._pool._call_with_failover(
            "embeddings", "embeddings.create", **kwargs
        )


def _parse_retry_after(err: RateLimitError) -> float:
    """Extract Retry-After header from a 429; fall back to 60s."""
    try:
        response = getattr(err, "response", None)
        if response is not None and getattr(response, "headers", None):
            retry_after = response.headers.get("retry-after") or response.headers.get(
                "Retry-After"
            )
            if retry_after:
                return float(retry_after)
    except Exception:
        pass
    return 60.0


_pool: AIClientPool | None = None


def get_ai_client() -> AIClientPool:
    """Return the shared AI client pool, building it on first call."""
    global _pool
    if _pool is not None:
        return _pool

    endpoints: list[_Endpoint] = []

    # Primary (always required)
    if settings.azure_openai_api_key and settings.azure_openai_endpoint:
        endpoints.append(
            _Endpoint(
                name=f"primary ({_region(settings.azure_openai_endpoint)})",
                client=AsyncAzureOpenAI(
                    api_key=settings.azure_openai_api_key,
                    azure_endpoint=settings.azure_openai_endpoint,
                    api_version=settings.azure_openai_api_version,
                    # Disable SDK auto-retry so WE control 429 handling (swap endpoint
                    # instead of blocking on Retry-After).
                    max_retries=0,
                ),
            )
        )

    # Optional secondary
    if settings.azure_openai_api_key_2 and settings.azure_openai_endpoint_2:
        endpoints.append(
            _Endpoint(
                name=f"secondary ({_region(settings.azure_openai_endpoint_2)})",
                client=AsyncAzureOpenAI(
                    api_key=settings.azure_openai_api_key_2,
                    azure_endpoint=settings.azure_openai_endpoint_2,
                    api_version=settings.azure_openai_api_version,
                    max_retries=0,
                ),
            )
        )

    if not endpoints:
        raise RuntimeError(
            "No Azure OpenAI endpoints configured. Set ARTEMIS_AZURE_OPENAI_API_KEY "
            "and ARTEMIS_AZURE_OPENAI_ENDPOINT."
        )

    logger.info(f"AI client pool initialized with {len(endpoints)} endpoint(s)")
    for ep in endpoints:
        logger.info(f"  - {ep.name}")

    _pool = AIClientPool(endpoints)
    return _pool


def _region(endpoint_url: str) -> str:
    """Extract a short region hint from an Azure endpoint URL for logging."""
    # Example: https://artemis-resource.openai.azure.com → "artemis-resource"
    try:
        host = endpoint_url.split("//", 1)[-1].split("/", 1)[0]
        return host.split(".", 1)[0]
    except Exception:
        return "unknown"
