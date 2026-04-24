from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

redis_client: aioredis.Redis = aioredis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True,
    max_connections=50,
)


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    try:
        yield redis_client
    except Exception as e:
        logger.error("redis_error", error=str(e))
        raise


async def redis_set(key: str, value: str, ttl: int | None = None) -> None:
    if ttl:
        await redis_client.setex(key, ttl, value)
    else:
        await redis_client.set(key, value)


async def redis_get(key: str) -> str | None:
    return await redis_client.get(key)


async def redis_delete(key: str) -> None:
    await redis_client.delete(key)


async def redis_incr(key: str, ttl: int | None = None) -> int:
    count = await redis_client.incr(key)
    if ttl and count == 1:
        await redis_client.expire(key, ttl)
    return count
