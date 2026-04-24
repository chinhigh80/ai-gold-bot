"""NOWPayments IPN webhook handler."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status

from app.db.session import async_session_factory
from app.models.order import OrderStatus
from app.services import notification_service, order_service, payment_service
from app.services.referral_service import process_referral_bonus

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/nowpayments", status_code=status.HTTP_200_OK)
async def nowpayments_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_nowpayments_sig: str = Header(..., alias="x-nowpayments-sig"),
):
    """Handle NOWPayments IPN callback."""
    body = await request.body()

    # Read IPN secret from Redis (admin-configurable), fall back to .env
    from app.db.redis import redis_get
    from app.config import settings as _settings
    ipn_secret = await redis_get("admin:cfg:NOWPAYMENTS_IPN_SECRET") or _settings.NOWPAYMENTS_IPN_SECRET

    if not payment_service.verify_ipn_signature(body, x_nowpayments_sig, ipn_secret):
        logger.warning("invalid_nowpayments_signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = await request.json()
    payment_id = str(payload.get("payment_id", ""))
    payment_status = payload.get("payment_status", "")
    order_id = payload.get("order_id")

    logger.info(
        "nowpayments_webhook",
        payment_id=payment_id,
        status=payment_status,
        order_id=order_id,
    )

    if payment_service.is_payment_confirmed(payment_status):
        background_tasks.add_task(_handle_payment_confirmed, payment_id)
    elif payment_service.is_payment_failed(payment_status):
        background_tasks.add_task(_handle_payment_failed, payment_id)

    return {"received": True}


async def _handle_payment_confirmed(payment_id: str) -> None:
    async with async_session_factory() as db:
        try:
            order = await order_service.get_order_by_payment_id(db, payment_id)
            if not order or order.status == OrderStatus.COMPLETED:
                return

            from app.models.user import User
            from sqlalchemy import select
            user_result = await db.execute(select(User).where(User.id == order.user_id))
            user = user_result.scalar_one()

            order = await order_service.complete_buy_order(db, order)
            await process_referral_bonus(db, user, order.total_usd)
            await db.commit()

            # Notify user
            msg = (
                f"✅ <b>Payment Confirmed!</b>\n\n"
                f"🥇 <b>{order.grams}g gold</b> has been added to your vault.\n"
                f"💰 Total paid: <b>${order.total_usd:,.2f}</b>\n\n"
                f"Your gold is ready. Trade wisely. 🌟"
            )
            await notification_service.notify_user(user.telegram_id, msg)
            await notification_service.notify_admins(
                f"🟢 New buy order completed!\nUser: {user.username or user.telegram_id}\n"
                f"Grams: {order.grams}g | Total: ${order.total_usd:,.2f}"
            )
        except Exception as e:
            logger.error("payment_confirmed_handler_failed", payment_id=payment_id, error=str(e))
            await db.rollback()


async def _handle_payment_failed(payment_id: str) -> None:
    async with async_session_factory() as db:
        try:
            order = await order_service.get_order_by_payment_id(db, payment_id)
            if not order:
                return
            order.status = OrderStatus.FAILED
            await db.commit()

            from app.models.user import User
            from sqlalchemy import select
            user_result = await db.execute(select(User).where(User.id == order.user_id))
            user = user_result.scalar_one()

            await notification_service.notify_user(
                user.telegram_id,
                "❌ <b>Payment failed or expired.</b>\n\nPlease try again or contact support.",
            )
        except Exception as e:
            logger.error("payment_failed_handler_failed", payment_id=payment_id, error=str(e))
            await db.rollback()
