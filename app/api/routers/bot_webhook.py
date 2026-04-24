"""Telegram bot webhook endpoint."""
from fastapi import APIRouter, Header, HTTPException, Request

from app.config import settings

router = APIRouter()


@router.post("/webhook")
async def bot_webhook(request: Request, x_telegram_bot_api_secret_token: str = Header(None)):
    """Receive updates from Telegram via webhook."""
    if settings.WEBHOOK_SECRET and x_telegram_bot_api_secret_token != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    from aiogram import Bot, Dispatcher
    from aiogram.types import Update

    body = await request.json()
    # The bot dispatcher is initialized in bot/main.py and shared via app state
    dp: Dispatcher = request.app.state.dp
    bot: Bot = request.app.state.bot

    update = Update.model_validate(body)
    await dp.feed_update(bot, update)
    return {"ok": True}
