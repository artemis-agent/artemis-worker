"""Job-related internal API routes: scrape, embed, monitor."""

import logging

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from artemis.core.config import settings

logger = logging.getLogger("artemis.api.jobs")


async def trigger_scrape(request: Request) -> JSONResponse:
    body = await request.json()
    company_id = body.get("company_id")
    query = body.get("query", "")
    limit = body.get("limit", 50)

    if not company_id:
        return JSONResponse({"error": "company_id required"}, status_code=400)

    from artemis.workers.scrape import scrape_company_task

    result = scrape_company_task.apply_async(args=[company_id], kwargs={"query": query, "limit": limit}, queue="scrape")

    return JSONResponse(
        {
            "status": "queued",
            "job_id": result.id,
            "company_id": company_id,
        }
    )


async def embed_text(request: Request) -> JSONResponse:
    body = await request.json()
    text = body.get("text", "")

    if not text:
        return JSONResponse({"error": "text required"}, status_code=400)

    from artemis.core.ai import get_ai_client

    client = get_ai_client()
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=[text],
    )
    embedding = response.data[0].embedding

    return JSONResponse({"embedding": embedding})


async def trigger_monitor(request: Request) -> JSONResponse:
    from artemis.workers.monitor import monitor_check_task

    result = monitor_check_task.apply_async(queue="monitor")
    return JSONResponse({"status": "queued", "job_id": result.id})


async def hunt_company(request: Request) -> JSONResponse:
    """Hunt a company: find careers page, detect ATS, create config."""
    body = await request.json()
    company_name = body.get("company_name", "").strip()
    careers_url = body.get("careers_url")

    if not company_name:
        return JSONResponse({"error": "company_name required"}, status_code=400)

    if body.get("async", False):
        from artemis.workers.scrape import hunt_company_task

        result = hunt_company_task.apply_async(args=[company_name, careers_url], queue="scrape")
        return JSONResponse({"status": "queued", "job_id": result.id})

    from artemis.services.hunt import hunt_company as _hunt

    result = await _hunt(company_name, careers_url=careers_url)
    return JSONResponse(result)


async def trigger_discovery(request: Request) -> JSONResponse:
    """Run autonomous discovery agent."""
    body = await request.json()
    sources = body.get("sources")
    max_companies = body.get("max_companies", 50)

    from artemis.workers.scrape import discovery_agent_task

    result = discovery_agent_task.apply_async(args=[sources, max_companies], queue="scrape")

    return JSONResponse({"status": "queued", "job_id": result.id})


routes = [
    Route("/internal/scrape", trigger_scrape, methods=["POST"]),
    Route("/internal/embed", embed_text, methods=["POST"]),
    Route("/internal/monitor/trigger", trigger_monitor, methods=["POST"]),
    Route("/internal/hunt", hunt_company, methods=["POST"]),
    Route("/internal/discover", trigger_discovery, methods=["POST"]),
]
