"""Message delivery helpers.

Every screen — whether triggered by a command or a button tap — shows a fresh
gold image. Old bot messages are deleted first so the chat stays clean.
"""
from __future__ import annotations

import structlog
from aiogram.types import InlineKeyboardMarkup, Message

logger = structlog.get_logger(__name__)

_CAPTION_LIMIT = 1024


async def _delete_quietly(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        pass


async def _send_with_photo(
    target: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None,
    context: str,
) -> Message:
    """
    Send a new message with a gold photo.
    Falls back to plain text if the photo can't be delivered or text exceeds 1024 chars.
    """
    from app.services.image_service import cache_photo_file_id, get_gold_photo_input

    if len(text) <= _CAPTION_LIMIT:
        try:
            photo = await get_gold_photo_input(context)
            msg = await target.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=reply_markup,
            )
            if msg.photo:
                await cache_photo_file_id(context, msg.photo[-1].file_id)
            return msg
        except Exception as exc:
            logger.warning("photo_send_failed", context=context, error=str(exc))

    # Text fallback
    return await target.answer(text, reply_markup=reply_markup, parse_mode="HTML")


async def safe_edit(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    context: str = "default",
) -> Message:
    """
    Called from callback handlers. Deletes the old message and sends a fresh
    gold-photo message in its place.
    """
    await _delete_quietly(message)
    return await _send_with_photo(message, text, reply_markup, context)


async def gold_reply(
    event,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
    context: str = "default",
) -> Message:
    """
    Universal helper for both commands (Message) and button taps (CallbackQuery).
    Always produces a fresh message with a gold photo.
    """
    from aiogram.types import CallbackQuery

    if isinstance(event, CallbackQuery):
        await _delete_quietly(event.message)
        await event.answer()
        target = event.message
    else:
        target = event

    return await _send_with_photo(target, text, keyboard, context)
