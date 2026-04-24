from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.order import Order, OrderStatus, OrderType
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.user import User
from app.services.price_service import calculate_buy_price, calculate_sell_price, get_gold_price

logger = structlog.get_logger(__name__)


async def create_buy_order(
    db: AsyncSession,
    user: User,
    grams: float,
    crypto_currency: str = "USDT",
    markup_percent: float | None = None,
) -> Order:
    """Create a new buy order with price calculation."""
    price_data = await get_gold_price()
    calc = calculate_buy_price(price_data.price_per_gram_usd, grams, markup_percent)

    now = datetime.now(timezone.utc)
    lock_expires = now + timedelta(seconds=settings.PRICE_LOCK_DURATION)

    order = Order(
        user_id=user.id,
        order_type=OrderType.BUY,
        grams=grams,
        price_per_gram_usd=calc["price_per_gram_usd"],
        base_price_per_gram_usd=calc["base_price_per_gram_usd"],
        total_usd=calc["total_usd"],
        markup_percent=calc["markup_percent"],
        spread_percent=0.0,
        status=OrderStatus.PRICE_LOCKED,
        crypto_currency=crypto_currency,
        price_locked_at=now,
        price_lock_expires_at=lock_expires,
    )
    db.add(order)
    await db.flush()
    await db.refresh(order)

    logger.info(
        "buy_order_created",
        order_id=order.id,
        user_id=user.id,
        grams=grams,
        total_usd=calc["total_usd"],
    )
    return order


async def create_sell_order(
    db: AsyncSession,
    user: User,
    grams: float,
    withdrawal_crypto: str,
    withdrawal_wallet: str,
    spread_percent: float | None = None,
) -> Order:
    """Create a new sell order (requires admin approval for payout)."""
    if user.gold_grams < grams:
        raise ValueError(f"Insufficient gold balance: {user.gold_grams:.4f}g available")

    price_data = await get_gold_price()
    calc = calculate_sell_price(price_data.price_per_gram_usd, grams, spread_percent)

    order = Order(
        user_id=user.id,
        order_type=OrderType.SELL,
        grams=grams,
        price_per_gram_usd=calc["price_per_gram_usd"],
        base_price_per_gram_usd=calc["base_price_per_gram_usd"],
        total_usd=calc["total_usd"],
        markup_percent=0.0,
        spread_percent=calc["spread_percent"],
        status=OrderStatus.PENDING,
        withdrawal_crypto=withdrawal_crypto,
        withdrawal_wallet=withdrawal_wallet,
    )

    # Reserve gold immediately
    user.gold_grams = round(user.gold_grams - grams, 8)

    db.add(order)
    await db.flush()
    await db.refresh(order)

    # Record pending transaction
    txn = Transaction(
        user_id=user.id,
        transaction_type=TransactionType.SELL,
        amount_usd=calc["total_usd"],
        gold_grams=grams,
        status=TransactionStatus.PENDING,
        reference_id=str(order.id),
        description=f"Sell {grams}g gold → {withdrawal_crypto}",
        balance_before_usd=user.balance_usd,
        balance_after_usd=user.balance_usd,
        gold_before=user.gold_grams + grams,
        gold_after=user.gold_grams,
    )
    db.add(txn)
    await db.flush()

    logger.info(
        "sell_order_created",
        order_id=order.id,
        user_id=user.id,
        grams=grams,
        total_usd=calc["total_usd"],
    )
    return order


async def complete_buy_order(db: AsyncSession, order: Order) -> Order:
    """Mark a buy order as completed after payment confirmed."""
    user_result = await db.execute(select(User).where(User.id == order.user_id))
    user = user_result.scalar_one()

    prev_balance = user.balance_usd
    prev_gold = user.gold_grams

    user.gold_grams = round(user.gold_grams + order.grams, 8)

    order.status = OrderStatus.COMPLETED

    txn = Transaction(
        user_id=user.id,
        transaction_type=TransactionType.BUY,
        amount_usd=order.total_usd,
        gold_grams=order.grams,
        status=TransactionStatus.COMPLETED,
        reference_id=str(order.id),
        description=f"Buy {order.grams}g gold",
        balance_before_usd=prev_balance,
        balance_after_usd=user.balance_usd,
        gold_before=prev_gold,
        gold_after=user.gold_grams,
    )
    db.add(txn)
    await db.flush()

    logger.info("buy_order_completed", order_id=order.id, user_id=user.id)
    return order


async def get_order_by_id(db: AsyncSession, order_id: int) -> Optional[Order]:
    result = await db.execute(select(Order).where(Order.id == order_id))
    return result.scalar_one_or_none()


async def get_order_by_payment_id(db: AsyncSession, payment_id: str) -> Optional[Order]:
    result = await db.execute(select(Order).where(Order.payment_id == payment_id))
    return result.scalar_one_or_none()


async def get_user_orders(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 20
) -> list[Order]:
    result = await db.execute(
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_all_orders(
    db: AsyncSession, skip: int = 0, limit: int = 100, status: OrderStatus | None = None
) -> list[Order]:
    query = select(Order).order_by(Order.created_at.desc())
    if status:
        query = query.where(Order.status == status)
    result = await db.execute(query.offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_revenue_stats(db: AsyncSession) -> dict:
    from sqlalchemy import and_

    result = await db.execute(
        select(func.sum(Order.total_usd), func.count(Order.id)).where(
            and_(Order.status == OrderStatus.COMPLETED, Order.order_type == OrderType.BUY)
        )
    )
    row = result.one()
    return {"total_revenue_usd": float(row[0] or 0), "total_orders": int(row[1] or 0)}
