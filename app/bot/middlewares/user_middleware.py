from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import get_or_create_user


class UserRegistrationMiddleware(BaseMiddleware):
    """Auto-register or fetch user on every update."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        db: AsyncSession | None = data.get("db")

        if tg_user and db:
            user, _ = await get_or_create_user(
                db,
                telegram_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                language_code=tg_user.language_code or "en",
            )
            data["user"] = user

        return await handler(event, data)
