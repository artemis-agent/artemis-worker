"""MinIO/S3 storage for resume files."""

import logging

import aioboto3

from artemis.core.config import settings

logger = logging.getLogger("artemis.resume.storage")


def _get_session() -> aioboto3.Session:
    return aioboto3.Session(
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )


async def download_resume(s3_key: str) -> bytes:
    """Download a resume PDF from MinIO."""
    session = _get_session()
    async with session.client("s3", endpoint_url=settings.s3_endpoint) as s3:
        resp = await s3.get_object(Bucket=settings.s3_bucket, Key=s3_key)
        return await resp["Body"].read()
