"""Starlette application with all internal API routes."""

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from artemis.api.routes.jobs import routes as job_routes
from artemis.api.routes.users import routes as user_routes


async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


routes = [
    Route("/healthz", healthz, methods=["GET"]),
    *job_routes,
    *user_routes,
]

app = Starlette(routes=routes)
