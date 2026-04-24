from __future__ import annotations

from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.user import User
from app.models.withdrawal import Withdrawal, WithdrawalStatus
from app.services.price_service import get_gold_price

logger = structlog.get_logger(__name__)


async def create_withdrawal_request(
    db: AsyncSession,
    user: User,
    grams: float,
    crypto_type: str,
    wallet_address: str,
) -> Withdrawal:
    """Create a pending withdrawal request for admin approval."""
    if user.gold_grams < grams:
        raise ValueError(f"Insufficient gold: {user.gold_grams:.4f}g available, {grams}g requested")

    price_data = await get_gold_price()
    from app.config import settings
    spread = settings.SPREAD_PERCENT
    net_price = price_data.price_per_gram_usd * (1 - spread / 100)
    amount_usd = round(net_price * grams, 2)

    withdrawal = Withdrawal(
        user_id=user.id,
        amount_usd=amount_usd,
        gold_grams=grams,
        crypto_type=crypto_type,
        wallet_address=wallet_address,
        gold_price_per_gram_usd=price_data.price_per_gram_usd,
        spread_percent=spread,
        status=WithdrawalStatus.PENDING,
    )

    user.gold_grams = round(user.gold_grams - grams, 8)

    db.add(withdrawal)
    await db.flush()
    await db.refresh(withdrawal)

    logger.info(
        "withdrawal_created",
        withdrawal_id=withdrawal.id,
        user_id=user.id,
        grams=grams,
        amount_usd=amount_usd,
        crypto=crypto_type,
    )
    return withdrawal


async def approve_withdrawal(
    db: AsyncSession, withdrawal_id: int, admin_notes: str | None = None
) -> Optional[Withdrawal]:
    result = await db.execute(select(Withdrawal).where(Withdrawal.id == withdrawal_id))
    withdrawal = result.scalar_one_or_none()
    if not withdrawal:
        return None

    withdrawal.status = WithdrawalStatus.APPROVED
    if admin_notes:
        withdrawal.admin_notes = admin_notes
    await db.flush()

    logger.info("withdrawal_approved", withdrawal_id=withdrawal_id)
    return withdrawal


async def reject_withdrawal(
    db: AsyncSession, withdrawal_id: int, admin_notes: str | None = None
) -> Optional[Withdrawal]:
    result = await db.execute(select(Withdrawal).where(Withdrawal.id == withdrawal_id))
    withdrawal = result.scalar_one_or_none()
    if not withdrawal:
        return None

    withdrawal.status = WithdrawalStatus.REJECTED
    if admin_notes:
        withdrawal.admin_notes = admin_notes

    # Refund gold to user
    user_result = await db.execute(select(User).where(User.id == withdrawal.user_id))
    user = user_result.scalar_one()
    user.gold_grams = round(user.gold_grams + withdrawal.gold_grams, 8)

    await db.flush()

    logger.info("withdrawal_rejected", withdrawal_id=withdrawal_id)
    return withdrawal


async def complete_withdrawal(
    db: AsyncSession, withdrawal_id: int, tx_hash: str
) -> Optional[Withdrawal]:
    result = await db.execute(select(Withdrawal).where(Withdrawal.id == withdrawal_id))
    withdrawal = result.scalar_one_or_none()
    if not withdrawal:
        return None

    withdrawal.status = WithdrawalStatus.COMPLETED
    withdrawal.tx_hash = tx_hash

    # Record transaction
    user_result = await db.execute(select(User).where(User.id == withdrawal.user_id))
    user = user_result.scalar_one()

    txn = Transaction(
        user_id=user.id,
        transaction_type=TransactionType.WITHDRAWAL,
        amount_usd=withdrawal.amount_usd,
        gold_grams=withdrawal.gold_grams,
        status=TransactionStatus.COMPLETED,
        reference_id=str(withdrawal_id),
        description=f"Withdrawal {withdrawal.gold_grams}g → {withdrawal.crypto_type}",
        balance_before_usd=user.balance_usd,
        balance_after_usd=user.balance_usd,
        gold_before=user.gold_grams + withdrawal.gold_grams,
        gold_after=user.gold_grams,
    )
    db.add(txn)
    await db.flush()

    logger.info("withdrawal_completed", withdrawal_id=withdrawal_id, tx_hash=tx_hash)
    return withdrawal


async def get_pending_withdrawals(db: AsyncSession) -> list[Withdrawal]:
    result = await db.execute(
        select(Withdrawal)
        .where(Withdrawal.status == WithdrawalStatus.PENDING)
        .order_by(Withdrawal.created_at.asc())
    )
    return list(result.scalars().all())


async def get_user_withdrawals(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 20
) -> list[Withdrawal]:
    result = await db.execute(
        select(Withdrawal)
        .where(Withdrawal.user_id == user_id)
        .order_by(Withdrawal.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())
