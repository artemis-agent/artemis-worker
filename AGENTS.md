# Artemis Worker

Python 3.12+ job scraping engine. Discovers company career pages, scrapes jobs via ATS-platform-specific scrapers, normalizes/enriches with AI, and monitors for changes.

## Tech Stack
- **Python 3.12+** with setuptools (`pyproject.toml`)
- **SQLAlchemy 2.0** (async) + **pgvector** on PostgreSQL 16
- **Celery** (Redis broker) for async job queues: `scrape`, `enrich`, `monitor`
- **Starlette + Uvicorn** internal API (port 8081) consumed by Go API
- **OpenAI** for AI enrichment, embeddings, and discovery
- **MinIO/S3** (aioboto3) for resume storage
- **DuckDuckGo** (ddgs) for web search

## Entry Points
- CLI: `artemis --help` (via `pyproject.toml` console_scripts)
- Internal API: `artemis serve-internal` (or `uvicorn artemis.internal_api:app`)

## Key Commands
| Command | Purpose |
|---------|---------|
| `artemis init-db` | Create all DB tables, indexes, pgvector extension |
| `artemis sync-configs` | Load ~1288 company YAMLs from `configs/companies/` into DB |
| `artemis hunt <name>` | Discover a company: search careers page, detect ATS, create YAML config |
| `artemis scrape <slug>` | Scrape jobs for one company |
| `artemis scrape-all` | Scrape all active companies |
| `artemis enrich` | Normalize + embed unenriched jobs |
| `artemis discover` | Batch discovery from fortune500, cloud100, yc, crunchbase sources |
| `artemis monitor` | Check active jobs for liveness |
| `artemis events` | Consume job change events from Redis Streams |

## Project Structure
```
artemis/
  cli.py              -- Click CLI (all commands)
  core/               -- database.py, models.py, config.py, ai.py, celery_app.py, redis.py, prompts.py
  scrapers/           -- base.py, registry.py, ats/* (greenhouse, lever, ashby, workday, etc.)
  services/           -- scrape.py, enrich.py, hunt.py, monitor.py, user.py
  workers/            -- Celery task definitions (scrape, enrich, monitor)
  discovery/          -- agent.py, bulk.py, detector.py, probe.py, runner.py, search.py, sources.py
  normalizer/         -- rules.py, skill_taxonomy.py
  monitor/            -- checker.py, events.py, webhook.py
  resume/             -- storage.py (MinIO/S3)
  api/                -- internal API routes, schemas.py
  internal_api.py     -- uvicorn runner
configs/companies/    -- 1288 YAML company configs (one per company, ATS-typed)
scripts/              -- ad-hoc scripts (bulk agent, debug, demos, benchmarks)
tests/                -- pytest with async support
```

## Patterns
- All DB access is async (`async_session` from `core.database`). Use `asyncio.run()` at CLI boundaries.
- Scrapers follow a base class in `scrapers/base.py` registered in `scrapers/registry.py`.
- Company configs are YAML files at `configs/companies/{slug}.yaml` with ATS type, careers URL, and settings.
- The Go API (`artemis-api`) consumes the internal API (`serve-internal`) for scrape/enrich/vector search.

## Environment
Config loaded from `.env` (see `.env.example`) via `pydantic-settings`. Key vars: `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, `S3_*`, `GITHUB_TOKEN`.

## Running Tests
```bash
pytest tests/
```
CI: lint with `ruff`, test with `pytest` (unit + e2e). See `.github/workflows/ci.yml`.
