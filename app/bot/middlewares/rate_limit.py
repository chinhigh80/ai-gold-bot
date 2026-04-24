from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.db.redis import redis_incr

logger = structlog.get_logger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit: int = 30) -> None:
        self.limit = limit

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        key = f"rate_limit:{user.id}"
        count = await redis_incr(key, ttl=60)

        if count > self.limit:
            logger.warning("rate_limit_exceeded", user_id=user.id, count=count)
            if isinstance(event, Message):
                await event.answer(
                    "⚠️ <b>Too many requests.</b>\nPlease slow down and try again in a minute.",
                )
            return None

        return await handler(event, data)
