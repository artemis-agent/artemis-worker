"""
Enrich service — normalize + embed jobs via LLM.

Merges the old normalizer/{workflow,normalizer,embedder}.py into a single
clean module. Uses core/ai.py singleton, core/prompts.py for prompts.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update

from artemis.core.ai import get_ai_client
from artemis.core.config import settings
from artemis.core.database import async_session
from artemis.core.models import Job
from artemis.core.prompts import NORMALIZE_JOB
from artemis.core.redis import get_redis

logger = logging.getLogger("artemis.services.enrich")

MAX_RETRIES = 3
QUEUE_KEY = "artemis:enrich_queue"
LAST_FLUSH_KEY = "artemis:enrich_last_flush"


# ── Queue management ──────────────────────────────────────────────────────


async def enqueue_jobs(job_ids: list[UUID]) -> int:
    """Push job IDs onto the enrichment queue. Triggers flush if threshold hit."""
    if not job_ids:
        return 0
    rdb = await get_redis()
    await rdb.rpush(QUEUE_KEY, *[str(jid) for jid in job_ids])
    depth = await rdb.llen(QUEUE_KEY)

    # Auto-trigger flush when threshold is reached
    if depth >= settings.enrich_batch_threshold:
        try:
            from artemis.workers.enrich import enrich_flush_task

            enrich_flush_task.apply_async(queue="enrich")
            logger.info(f"auto-triggered enrich flush (queue depth: {depth})")
        except Exception as e:
            logger.warning(f"failed to auto-trigger flush: {e}")

    return depth


async def should_flush() -> tuple[bool, int]:
    """Check if we should process the queue."""
    rdb = await get_redis()
    depth = await rdb.llen(QUEUE_KEY)
    if depth == 0:
        return False, 0
    if depth >= settings.enrich_batch_threshold:
        return True, depth
    last_flush = await rdb.get(LAST_FLUSH_KEY)
    if last_flush is None:
        return True, depth
    if time.time() - float(last_flush) >= settings.enrich_flush_interval:
        return True, depth
    return False, depth


async def drain_queue(max_items: int = 500) -> list[str]:
    """Atomically drain up to max_items from the queue."""
    rdb = await get_redis()
    lua = """
    local items = redis.call('LRANGE', KEYS[1], 0, ARGV[1] - 1)
    if #items > 0 then
        redis.call('LTRIM', KEYS[1], ARGV[1], -1)
    end
    redis.call('SET', KEYS[2], ARGV[2])
    return items
    """
    return await rdb.eval(lua, 2, QUEUE_KEY, LAST_FLUSH_KEY, max_items, str(time.time())) or []


# ── Embedding text composition ────────────────────────────────────────────


def compose_embedding_text(metadata: dict, description: str | None = None) -> str:
    """Build rich embedding input from normalized job metadata + description.

    Format: role context | skill signals | location signals | description excerpt
    """
    parts = []

    # Role identity: title + seniority + department
    role_parts = []
    if metadata.get("canonical_title"):
        role_parts.append(metadata["canonical_title"])
    if metadata.get("seniority_level"):
        role_parts.append(f"{metadata['seniority_level']} level")
    if metadata.get("department"):
        role_parts.append(f"in {metadata['department']}")
    if metadata.get("employment_type"):
        role_parts.append(metadata["employment_type"])
    if role_parts:
        parts.append(" ".join(role_parts))

    # Skills
    if metadata.get("skills"):
        parts.append("Skills: " + ", ".join(metadata["skills"][:25]))

    # Location + remote type
    loc_parts = []
    loc = metadata.get("normalized_location", {})
    if isinstance(loc, dict):
        loc_str = ", ".join(
            p for p in [loc.get("city", ""), loc.get("state", ""), loc.get("country", "")] if p and isinstance(p, str)
        )
    elif isinstance(loc, str):
        loc_str = loc
    else:
        loc_str = ""
    if loc_str:
        loc_parts.append(loc_str)
    if metadata.get("remote_type"):
        loc_parts.append(metadata["remote_type"])
    if loc_parts:
        parts.append(" ".join(loc_parts))

    # Experience expectations
    if metadata.get("experience_range"):
        parts.append(f"Experience: {metadata['experience_range']}")

    text = " | ".join(parts)

    # Append description excerpt for semantic richness
    if description:
        # Take first 600 chars — captures responsibilities + requirements
        text += f" | {description[:600]}"
    return text


# ── Core enrichment steps ─────────────────────────────────────────────────


async def normalize_batch(jobs: list[Job], session) -> list[Job]:
    """Normalize a batch of jobs via LLM. Updates DB in-place."""
    unnormalized = [j for j in jobs if j.normalized_at is None]
    if not unnormalized:
        return jobs

    client = get_ai_client()
    normalized = []

    for i in range(0, len(unnormalized), 20):
        batch = unnormalized[i : i + 20]
        input_data = [
            {"title": j.title, "location": j.location or "", "description": (j.description or "")[:1000]} for j in batch
        ]

        for attempt in range(MAX_RETRIES):
            try:
                response = await client.chat.completions.create(
                    model=settings.llm_model,
                    messages=[
                        {"role": "system", "content": NORMALIZE_JOB},
                        {"role": "user", "content": json.dumps(input_data)},
                    ],
                    temperature=0,
                )

                content = response.choices[0].message.content
                if content.startswith("```"):
                    content = content.split("\n", 1)[1].rsplit("```", 1)[0]
                parsed = json.loads(content)
                items = parsed if isinstance(parsed, list) else parsed.get("jobs", parsed.get("results", []))

                for job, meta in zip(batch, items):
                    await session.execute(
                        update(Job)
                        .where(Job.id == job.id)
                        .values(
                            metadata_=meta,
                            normalized_at=datetime.now(timezone.utc),
                        )
                    )
                    job.metadata_ = meta
                    job.normalized_at = datetime.now(timezone.utc)
                    normalized.append(job)

                await session.commit()
                break
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logger.warning(f"normalize parse error (attempt {attempt + 1}): {e}")
                if attempt == MAX_RETRIES - 1:
                    logger.error(f"normalize batch failed after {MAX_RETRIES} attempts")
            except Exception as e:
                logger.warning(f"normalize API error (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2**attempt)
                else:
                    logger.error(f"normalize batch failed: {e}")

    logger.info(f"normalized {len(normalized)} jobs")
    return jobs


async def embed_batch(jobs: list[Job], session) -> int:
    """Generate embeddings for normalized jobs. Returns count embedded."""
    embeddable = [j for j in jobs if j.metadata_ is not None and j.embedding is None]
    if not embeddable:
        return 0

    client = get_ai_client()
    total = 0

    for i in range(0, len(embeddable), 100):
        batch = embeddable[i : i + 100]
        texts = [compose_embedding_text(j.metadata_ or {}, j.description) for j in batch]

        for attempt in range(MAX_RETRIES):
            try:
                response = await client.embeddings.create(
                    model=settings.embedding_model,
                    input=texts,
                )
                for job, emb_data in zip(batch, response.data):
                    await session.execute(
                        update(Job)
                        .where(Job.id == job.id)
                        .values(
                            embedding=emb_data.embedding,
                            embedded_at=datetime.now(timezone.utc),
                        )
                    )
                    total += 1
                await session.commit()
                break
            except Exception as e:
                logger.warning(f"embed API error (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2**attempt)
                else:
                    logger.error(f"embed batch failed: {e}")

    logger.info(f"embedded {total} jobs")
    return total


async def summarize_batch(jobs: list[Job], session) -> int:
    """Generate 1-line short summaries for jobs missing them. Returns count."""
    need_summary = [j for j in jobs if j.description and not j.short_summary]
    if not need_summary:
        return 0

    client = get_ai_client()
    total = 0

    for i in range(0, len(need_summary), 20):
        batch = need_summary[i : i + 20]
        input_texts = []
        for j in batch:
            input_texts.append(f"Title: {j.title}\nDescription: {(j.description or '')[:800]}")

        prompt = (
            "For each job below, write a single concise sentence (max 120 chars) summarizing the role. "
            "Focus on: what the person does, key technology, and team/domain. "
            "Return a JSON array of strings, one per job. No markdown.\n\n"
            + "\n---\n".join(f"[{idx}] {t}" for idx, t in enumerate(input_texts))
        )

        for attempt in range(MAX_RETRIES):
            try:
                response = await client.chat.completions.create(
                    model=settings.llm_model,
                    messages=[
                        {"role": "system", "content": "You generate brief job summaries. Return only valid JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0,
                )

                content = response.choices[0].message.content
                if content.startswith("```"):
                    content = content.split("\n", 1)[1].rsplit("```", 1)[0]
                summaries = json.loads(content)
                if not isinstance(summaries, list):
                    summaries = summaries.get("summaries", [])

                for job, summary in zip(batch, summaries):
                    if summary and isinstance(summary, str):
                        await session.execute(
                            update(Job)
                            .where(Job.id == job.id)
                            .values(
                                short_summary=summary[:200],
                            )
                        )
                        total += 1
                await session.commit()
                break
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"summarize parse error (attempt {attempt + 1}): {e}")
                if attempt == MAX_RETRIES - 1:
                    logger.error(f"summarize batch failed after {MAX_RETRIES} attempts")
            except Exception as e:
                logger.warning(f"summarize API error (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2**attempt)
                else:
                    logger.error(f"summarize batch failed: {e}")

    logger.info(f"summarized {total} jobs")
    return total


# ── Public API ────────────────────────────────────────────────────────────


async def enrich_jobs(job_ids: list[str]) -> dict:
    """Full enrichment pipeline: normalize → embed. Returns stats."""
    if not job_ids:
        return {"normalized": 0, "embedded": 0}

    async with async_session() as session:
        uuids = [UUID(jid) for jid in job_ids]
        result = await session.execute(select(Job).where(Job.id.in_(uuids)))
        jobs = list(result.scalars().all())
        if not jobs:
            return {"normalized": 0, "embedded": 0}

        jobs = await normalize_batch(jobs, session)
        embedded = await embed_batch(jobs, session)
        summarized = await summarize_batch(jobs, session)

    return {
        "normalized": len([j for j in jobs if j.normalized_at]),
        "embedded": embedded,
        "summarized": summarized,
    }


async def flush_enrichment_queue() -> dict:
    """Drain the queue and run enrichment on all items."""
    job_ids = await drain_queue()
    if not job_ids:
        return {"drained": 0, "normalized": 0, "embedded": 0}

    logger.info(f"flushing {len(job_ids)} jobs from queue")
    result = await enrich_jobs(job_ids)
    result["drained"] = len(job_ids)
    return result
