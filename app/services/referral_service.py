from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.user import User

logger = structlog.get_logger(__name__)


async def process_referral_bonus(
    db: AsyncSession, new_user: User, first_order_amount_usd: float
) -> None:
    """Credit referrer with bonus when referred user completes first buy."""
    if not new_user.referred_by_id:
        return

    result = await db.execute(select(User).where(User.id == new_user.referred_by_id))
    referrer = result.scalar_one_or_none()
    if not referrer:
        return

    bonus = round(first_order_amount_usd * settings.REFERRAL_BONUS_PERCENT / 100, 2)
    if bonus <= 0:
        return

    prev_balance = referrer.balance_usd
    referrer.balance_usd = round(referrer.balance_usd + bonus, 2)
    referrer.referral_bonus_earned_usd = round(
        referrer.referral_bonus_earned_usd + bonus, 2
    )

    txn = Transaction(
        user_id=referrer.id,
        transaction_type=TransactionType.REFERRAL_BONUS,
        amount_usd=bonus,
        status=TransactionStatus.COMPLETED,
        reference_id=str(new_user.id),
        description=f"Referral bonus from user #{new_user.id}",
        balance_before_usd=prev_balance,
        balance_after_usd=referrer.balance_usd,
        gold_before=referrer.gold_grams,
        gold_after=referrer.gold_grams,
    )
    db.add(txn)
    await db.flush()

    logger.info(
        "referral_bonus_credited",
        referrer_id=referrer.id,
        new_user_id=new_user.id,
        bonus_usd=bonus,
    )
