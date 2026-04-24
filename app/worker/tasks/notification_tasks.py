"""Scheduled notification tasks."""
import asyncio

import structlog

from app.worker.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="app.worker.tasks.notification_tasks.daily_price_broadcast")
def daily_price_broadcast():
    """Send daily gold price update to all active users."""

    async def _run():
        from sqlalchemy import select

        from app.db.session import async_session_factory
        from app.models.user import User
        from app.services.notification_service import broadcast_message
        from app.services.price_service import calculate_buy_price, calculate_sell_price, get_gold_price

        try:
            price_data = await get_gold_price()
            buy = calculate_buy_price(price_data.price_per_gram_usd, 1.0)
            sell = calculate_sell_price(price_data.price_per_gram_usd, 1.0)
        except Exception as e:
            logger.error("daily_broadcast_price_failed", error=str(e))
            return {"sent": 0}

        message = (
            "✨ <b>GoldVault — Daily Gold Update</b>\n\n"
            f"📊 <b>Today's Rates (per gram):</b>\n"
            f"💰 Buy:  <b>${buy['price_per_gram_usd']:.4f}</b>\n"
            f"🔄 Sell: <b>${sell['price_per_gram_usd']:.4f}</b>\n\n"
            f"🏆 Spot: ${price_data.price_per_gram_usd:.4f}/g\n\n"
            f"<i>Trade now while rates are live. Use /buy or /sell to get started.</i>\n\n"
            f"— <b>GoldVault Team</b> 🥇"
        )

        async with async_session_factory() as db:
            result = await db.execute(
                select(User.telegram_id).where(
                    User.is_active == True, User.is_banned == False  # noqa: E712
                )
            )
            ids = [row[0] for row in result.all()]

        stats = await broadcast_message(ids, message)
        logger.info("daily_broadcast_sent", **stats)
        return stats

    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(_run())
    loop.close()
    return result


@celery_app.task(name="app.worker.tasks.notification_tasks.notify_admin_new_withdrawal")
def notify_admin_new_withdrawal(withdrawal_id: int, user_display: str, amount_usd: float):
    """Notify admins of a new withdrawal request."""

    async def _run():
        from app.services.notification_service import notify_admins
        await notify_admins(
            f"🔔 <b>New Withdrawal Request</b> #{withdrawal_id}\n"
            f"User: {user_display}\n"
            f"Amount: ${amount_usd:,.2f}\n\n"
            f"<a href='/admin/withdrawals'>Review in Admin Panel →</a>"
        )

    loop = asyncio.new_event_loop()
    loop.run_until_complete(_run())
    loop.close()
