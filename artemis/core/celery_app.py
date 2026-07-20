"""Celery application — single source of truth for task broker config."""

from celery import Celery
from celery.schedules import crontab

from artemis.core.config import settings

app = Celery("artemis")

app.conf.update(
    broker_url=settings.redis_url.replace("redis://", "redis://", 1),
    result_backend=settings.redis_url,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 min hard limit
    task_soft_time_limit=1500,  # 25 min soft limit
    worker_prefetch_multiplier=1,  # One task at a time for LLM workers
    task_routes={
        "artemis.workers.scrape.*": {"queue": "scrape"},
        "artemis.workers.enrich.*": {"queue": "enrich"},
        "artemis.workers.monitor.*": {"queue": "monitor"},
    },
    beat_schedule={
        "scrape-all-30min": {
            "task": "artemis.workers.scrape.scrape_all_task",
            "schedule": crontab(minute="0,30"),
        },
        "enrich-flush-safety": {
            "task": "artemis.workers.enrich.enrich_flush_task",
            "schedule": crontab(minute="0,30"),
        },
        "monitor-check": {
            "task": "artemis.workers.monitor.monitor_check_task",
            "schedule": crontab(minute="*/2"),
        },
        "agent-discover-daily": {
            "task": "artemis.workers.scrape.daily_agent_discover_task",
            "schedule": crontab(minute=0, hour=3),  # 03:00 UTC daily
            "kwargs": {"daily_cap": 30},
        },
    },
)

app.autodiscover_tasks(["artemis.workers.scrape", "artemis.workers.enrich", "artemis.workers.monitor"])
