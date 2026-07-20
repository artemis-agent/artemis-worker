"""Enrich worker — Celery task definitions for job enrichment + resume parsing."""

import asyncio
import logging

from artemis.core.celery_app import app

logger = logging.getLogger("artemis.workers.enrich")


@app.task(name="artemis.workers.enrich.enrich_flush_task", time_limit=1800)
def enrich_flush_task():
    """Drain the enrichment queue and run normalize + embed."""

    async def _run():
        from artemis.services.enrich import should_flush, flush_enrichment_queue

        flush, depth = await should_flush()
        if flush:
            logger.info(f"flushing enrichment queue ({depth} jobs)")
            result = await flush_enrichment_queue()
            logger.info(f"enrichment done: {result}")
            return result
        return {"skipped": True, "depth": depth}

    return asyncio.run(_run())


@app.task(name="artemis.workers.enrich.resume_parse_task", bind=True, max_retries=2)
def resume_parse_task(self, user_id: str, resume_id: str, s3_key: str):
    """Parse a resume PDF: extract → interpret → embed → store."""

    async def _run():
        from artemis.services.user import parse_and_store_resume

        logger.info(f"parsing resume {resume_id} for user {user_id}")
        result = await parse_and_store_resume(user_id, resume_id, s3_key)
        logger.info(f"resume {resume_id} parsed: {result['skills_count']} skills")
        return result

    return asyncio.run(_run())
