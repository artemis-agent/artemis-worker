"""
Webhook consumer for job status change events.

Reads from Redis Stream consumer group and forwards to webhook URL.
Can run as a standalone consumer or be called from the worker.
"""

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

import httpx

from artemis.monitor.events import consume_events, ack_events, ensure_consumer_group

logger = logging.getLogger("artemis.monitor.webhook")

CONSUMER_GROUP = "webhook"
CONSUMER_NAME = "webhook-worker-1"


async def run_webhook_consumer(webhook_url: str, webhook_secret: str = ""):
    """Long-running consumer that forwards stream events to a webhook URL."""
    if not webhook_url:
        logger.info("webhook consumer: no webhook_url configured, skipping")
        return

    await ensure_consumer_group(CONSUMER_GROUP)
    logger.info(f"webhook consumer started, forwarding to {webhook_url}")

    while True:
        events = await consume_events(CONSUMER_GROUP, CONSUMER_NAME, count=50, block_ms=5000)
        if not events:
            continue

        changes = [data for _, data in events]
        msg_ids = [msg_id for msg_id, _ in events]

        success = await _post_webhook(changes, webhook_url, webhook_secret)
        if success:
            await ack_events(CONSUMER_GROUP, msg_ids)
        else:
            logger.warning(f"webhook delivery failed, {len(msg_ids)} events will be redelivered")


async def _post_webhook(
    changes: list[dict],
    webhook_url: str,
    webhook_secret: str = "",
) -> bool:
    """POST batch of changes to webhook URL with HMAC signing and retry."""
    payload = json.dumps({
        "event": "job_status_changed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "changes": changes,
    }, default=str)

    headers = {"Content-Type": "application/json"}
    if webhook_secret:
        signature = hmac.new(
            webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={signature}"

    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                resp = await client.post(webhook_url, content=payload, headers=headers)
                if resp.status_code < 300:
                    logger.info(f"webhook delivered: {len(changes)} changes to {webhook_url}")
                    return True
                logger.warning(f"webhook returned {resp.status_code}, attempt {attempt + 1}/{max_retries}")
        except Exception as e:
            logger.warning(f"webhook failed attempt {attempt + 1}/{max_retries}: {e}")

        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)

    logger.error(f"webhook delivery failed after {max_retries} attempts")
    return False
