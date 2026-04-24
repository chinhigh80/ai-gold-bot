"""Aiogram 3.x bot entry point — supports both polling and webhook modes."""
from __future__ import annotations

import asyncio
import logging

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from app.bot.handlers import buy, referral, sell, start, support, transactions, wallet
from app.bot.middlewares.db_middleware import DbSessionMiddleware
from app.bot.middlewares.rate_limit import RateLimitMiddleware
from app.bot.middlewares.user_middleware import UserRegistrationMiddleware
from app.config import settings

logger = structlog.get_logger(__name__)

# Module-level bot reference so handlers can send proactive messages
_bot_instance: Bot | None = None


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


async def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage)

    # Middlewares (order matters)
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.message.middleware(RateLimitMiddleware(limit=settings.RATE_LIMIT_PER_MINUTE))
    dp.callback_query.middleware(RateLimitMiddleware(limit=settings.RATE_LIMIT_PER_MINUTE))
    dp.message.middleware(UserRegistrationMiddleware())
    dp.callback_query.middleware(UserRegistrationMiddleware())

    # Routers
    dp.include_router(start.router)
    dp.include_router(buy.router)
    dp.include_router(sell.router)
    dp.include_router(wallet.router)
    dp.include_router(transactions.router)
    dp.include_router(support.router)
    dp.include_router(referral.router)

    return bot, dp


async def _setup_bot_profile(bot: Bot) -> None:
    """Register commands and set description shown to new users."""
    from aiogram.types import BotCommand, BotCommandScopeDefault

    commands = [
        BotCommand(command="start",        description="🏠 Main Menu"),
        BotCommand(command="buy",          description="💰 Buy Gold"),
        BotCommand(command="sell",         description="🔄 Sell Gold"),
        BotCommand(command="wallet",       description="💳 My Vault & Balance"),
        BotCommand(command="transactions", description="📊 Transaction History"),
        BotCommand(command="referral",     description="👥 Referral Program"),
        BotCommand(command="support",      description="💬 Support & FAQ"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

    await bot.set_my_description(
        "✨ AMIRA GOLD LUXURY\n\n"
        "Buy & sell physical gold at live UAE market prices.\n\n"
        "• Real-time XAU/USD pricing\n"
        "• Instant crypto payouts — BTC, ETH, USDT\n"
        "• Secure digital vault, fully audited\n"
        "• 1% referral rewards, no limits\n"
        "• 24/7 support in English & Arabic\n\n"
        "Press START ▶ to open your vault."
    )
    await bot.set_my_short_description(
        "Buy & sell gold at live UAE prices. Instant BTC/ETH/USDT payouts."
    )
    logger.info("bot_profile_configured")


async def run_polling() -> None:
    setup_logging()
    bot, dp = await create_bot_and_dispatcher()

    global _bot_instance
    _bot_instance = bot

    me = await bot.get_me()
    logger.info("bot_starting_polling", username=me.username)

    await _setup_bot_profile(bot)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


async def run_webhook(app) -> None:
    """Register webhook and attach bot/dp to the FastAPI app state."""
    bot, dp = await create_bot_and_dispatcher()

    webhook_url = settings.webhook_url
    if webhook_url:
        await bot.set_webhook(
            url=webhook_url,
            secret_token=settings.WEBHOOK_SECRET,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
        )
        logger.info("webhook_set", url=webhook_url)

    app.state.bot = bot
    app.state.dp = dp
    return bot, dp


if __name__ == "__main__":
    asyncio.run(run_polling())
