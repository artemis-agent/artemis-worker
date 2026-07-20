"""MinIO/S3 storage for resume files."""

import logging
import uuid
from io import BytesIO

import aioboto3

from artemis.core.config import settings

logger = logging.getLogger("artemis.resume.storage")


def _get_session() -> aioboto3.Session:
    return aioboto3.Session(
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )


async def ensure_bucket():
    session = _get_session()
    async with session.client("s3", endpoint_url=settings.s3_endpoint) as s3:
        try:
            await s3.head_bucket(Bucket=settings.s3_bucket)
        except Exception:
            await s3.create_bucket(Bucket=settings.s3_bucket)
            logger.info(f"created bucket '{settings.s3_bucket}'")


async def upload_resume(file_data: bytes, filename: str, user_id: str) -> str:
    """Upload a resume PDF to MinIO. Returns the S3 key."""
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "pdf"
    s3_key = f"resumes/{user_id}/{uuid.uuid4().hex}.{ext}"

    session = _get_session()
    async with session.client("s3", endpoint_url=settings.s3_endpoint) as s3:
        await s3.upload_fileobj(
            BytesIO(file_data),
            settings.s3_bucket,
            s3_key,
            ExtraArgs={"ContentType": "application/pdf"},
        )
    logger.info(f"uploaded resume: {s3_key} ({len(file_data)} bytes)")
    return s3_key


async def download_resume(s3_key: str) -> bytes:
    """Download a resume PDF from MinIO."""
    session = _get_session()
    async with session.client("s3", endpoint_url=settings.s3_endpoint) as s3:
        resp = await s3.get_object(Bucket=settings.s3_bucket, Key=s3_key)
        return await resp["Body"].read()
