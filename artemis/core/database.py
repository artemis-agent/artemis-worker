import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from artemis.core.config import settings

# Celery workers wrap async tasks in asyncio.run(), which spins up a fresh event
# loop per task. asyncpg connections are bound to the loop they were created on,
# so cached connections from a previous loop fail with
# "another operation is in progress" when reused by a later task.
# Use NullPool inside Celery to make each session create a fresh connection.
_in_celery = bool(os.environ.get("CELERY_WORKER")) or any(
    "celery" in arg.lower() for arg in os.sys.argv
)

_engine_kwargs: dict = {"echo": False}
if _in_celery:
    _engine_kwargs["poolclass"] = NullPool
else:
    _engine_kwargs["pool_size"] = settings.db_pool_size
    _engine_kwargs["max_overflow"] = settings.db_max_overflow

engine = create_async_engine(settings.database_url, **_engine_kwargs)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
