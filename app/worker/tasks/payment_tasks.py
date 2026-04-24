"""Background tasks for payment confirmation polling and order expiry."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog

from app.worker.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="app.worker.tasks.payment_tasks.poll_pending_payments", bind=True)
def poll_pending_payments(self):
    """Poll NOWPayments for status updates on awaiting_payment orders."""

    async def _run():
        from sqlalchemy import select

        from app.db.session import async_session_factory
        from app.models.order import Order, OrderStatus
        from app.services import payment_service
        from app.services.order_service import complete_buy_order

        async with async_session_factory() as db:
            result = await db.execute(
                select(Order).where(Order.status == OrderStatus.AWAITING_PAYMENT)
            )
            orders = result.scalars().all()
            processed = 0

            for order in orders:
                if not order.payment_id:
                    continue
                try:
                    status_data = await payment_service.get_payment_status(order.payment_id)
                    status = status_data.get("payment_status", "")

                    if payment_service.is_payment_confirmed(status):
                        await complete_buy_order(db, order)
                        await db.commit()
                        processed += 1
                        logger.info("payment_confirmed_via_polling", order_id=order.id)

                    elif payment_service.is_payment_failed(status):
                        order.status = OrderStatus.FAILED
                        await db.commit()
                        logger.info("payment_failed_via_polling", order_id=order.id)

                except Exception as e:
                    logger.warning("payment_poll_failed", order_id=order.id, error=str(e))

            return processed

    loop = asyncio.new_event_loop()
    count = loop.run_until_complete(_run())
    loop.close()
    return {"processed": count}


@celery_app.task(name="app.worker.tasks.payment_tasks.expire_stale_orders")
def expire_stale_orders():
    """Expire orders whose price lock has passed and are still pending."""

    async def _run():
        from sqlalchemy import and_, select

        from app.db.session import async_session_factory
        from app.models.order import Order, OrderStatus

        now = datetime.now(timezone.utc)

        async with async_session_factory() as db:
            result = await db.execute(
                select(Order).where(
                    and_(
                        Order.status == OrderStatus.PRICE_LOCKED,
                        Order.price_lock_expires_at < now,
                    )
                )
            )
            orders = result.scalars().all()
            for order in orders:
                order.status = OrderStatus.EXPIRED
            await db.commit()
            return len(orders)

    loop = asyncio.new_event_loop()
    count = loop.run_until_complete(_run())
    loop.close()
    logger.info("orders_expired", count=count)
    return {"expired": count}
