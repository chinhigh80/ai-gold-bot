from __future__ import annotations

from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = structlog.get_logger(__name__)


async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_or_create_user(
    db: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    language_code: str = "en",
    referral_code: Optional[str] = None,
) -> tuple[User, bool]:
    """Get existing user or create new one. Returns (user, created)."""
    user = await get_user_by_telegram_id(db, telegram_id)
    if user:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        await db.flush()
        return user, False

    # Resolve referrer
    referred_by_id: Optional[int] = None
    if referral_code:
        result = await db.execute(select(User).where(User.referral_code == referral_code))
        referrer = result.scalar_one_or_none()
        if referrer:
            referred_by_id = referrer.id

    try:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            referred_by_id=referred_by_id,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        logger.info("user_created", telegram_id=telegram_id, username=username)
        return user, True
    except IntegrityError:
        await db.rollback()
        user = await get_user_by_telegram_id(db, telegram_id)
        if user:
            return user, False
        raise


async def get_all_users(
    db: AsyncSession, skip: int = 0, limit: int = 100, active_only: bool = True
) -> list[User]:
    query = select(User)
    if active_only:
        query = query.where(User.is_active == True, User.is_banned == False)  # noqa: E712
    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_users(db: AsyncSession) -> int:
    from sqlalchemy import func

    result = await db.execute(select(func.count(User.id)))
    return result.scalar_one()


async def ban_user(db: AsyncSession, user_id: int) -> Optional[User]:
    user = await get_user_by_id(db, user_id)
    if user:
        user.is_banned = True
        await db.flush()
    return user


async def unban_user(db: AsyncSession, user_id: int) -> Optional[User]:
    user = await get_user_by_id(db, user_id)
    if user:
        user.is_banned = False
        await db.flush()
    return user


async def update_user_balance(
    db: AsyncSession, user_id: int, delta_usd: float, delta_grams: float = 0.0
) -> Optional[User]:
    user = await get_user_by_id(db, user_id)
    if user:
        user.balance_usd = round(user.balance_usd + delta_usd, 8)
        user.gold_grams = round(user.gold_grams + delta_grams, 8)
        await db.flush()
    return user
