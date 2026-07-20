"""
Redis Streams event bus for job status changes.

Producer: monitor worker publishes change events via XADD.
Consumer: any service reads via XREADGROUP with consumer groups.

Stream key: artemis:events:job_changes
Consumer groups: each service creates its own group (webhook, analytics, etc.)
"""

import json
import logging
from datetime import datetime, timezone

import redis.asyncio as aioredis

from artemis.core.redis import get_redis

logger = logging.getLogger("artemis.monitor.events")

STREAM_KEY = "artemis:events:job_changes"
MAX_STREAM_LEN = 50_000  # Cap stream at 50K events (MAXLEN ~)


async def publish_changes(changes: list[dict]) -> int:
    """Publish job status change events to Redis Stream. Returns count published."""
    if not changes:
        return 0

    r = await get_redis()
    try:
        count = 0
        for change in changes:
            await r.xadd(
                STREAM_KEY,
                {
                    "event": "job_status_changed",
                    "data": json.dumps(change, default=str),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                maxlen=MAX_STREAM_LEN,
                approximate=True,
            )
            count += 1
        logger.info(f"published {count} events to {STREAM_KEY}")
        return count
    finally:
        pass  # shared pool, don't close


async def ensure_consumer_group(group_name: str) -> None:
    """Create a consumer group if it doesn't exist. Idempotent."""
    r = await get_redis()
    try:
        await r.xgroup_create(STREAM_KEY, group_name, id="0", mkstream=True)
        logger.info(f"created consumer group '{group_name}' on {STREAM_KEY}")
    except aioredis.ResponseError as e:
        if "BUSYGROUP" in str(e):
            pass
        else:
            raise


async def consume_events(
    group_name: str,
    consumer_name: str,
    count: int = 100,
    block_ms: int = 5000,
) -> list[tuple[str, dict]]:
    """
    Read events from stream using consumer group.

    Returns list of (message_id, event_data) tuples.
    Each message must be ACK'd after processing via ack_events().
    """
    await ensure_consumer_group(group_name)
    r = await get_redis()
    results = await r.xreadgroup(
        group_name,
        consumer_name,
        {STREAM_KEY: ">"},
        count=count,
        block=block_ms,
    )

    events = []
    if results:
        for stream_name, messages in results:
            for msg_id, fields in messages:
                try:
                    data = json.loads(fields.get("data", "{}"))
                except json.JSONDecodeError:
                    data = fields
                events.append((msg_id, data))
    return events


async def ack_events(group_name: str, message_ids: list[str]) -> int:
    """Acknowledge processed events. Returns count acknowledged."""
    if not message_ids:
        return 0
    r = await get_redis()
    return await r.xack(STREAM_KEY, group_name, *message_ids)


async def stream_info() -> dict:
    """Get stream metadata (length, groups, etc.)."""
    r = await get_redis()
    try:
        info = await r.xinfo_stream(STREAM_KEY)
        groups = await r.xinfo_groups(STREAM_KEY)
        return {
            "stream": STREAM_KEY,
            "length": info.get("length", 0),
            "first_entry": info.get("first-entry"),
            "last_entry": info.get("last-entry"),
            "groups": [
                {
                    "name": g.get("name"),
                    "consumers": g.get("consumers"),
                    "pending": g.get("pending"),
                    "last_delivered_id": g.get("last-delivered-id"),
                }
                for g in groups
            ],
        }
    except aioredis.ResponseError:
        return {"stream": STREAM_KEY, "length": 0, "groups": []}
