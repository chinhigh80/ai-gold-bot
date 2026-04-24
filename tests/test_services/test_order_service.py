"""Integration tests for order service logic."""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import OrderStatus, OrderType
from app.models.user import User
from app.services.user_service import get_or_create_user


@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    user, _ = await get_or_create_user(
        db, telegram_id=999999999, username="testuser", first_name="Test"
    )
    user.gold_grams = 100.0
    await db.flush()
    return user


@pytest.mark.asyncio
async def test_sell_insufficient_gold(db: AsyncSession, test_user: User):
    from app.services.order_service import create_sell_order

    with pytest.raises(ValueError, match="Insufficient gold"):
        await create_sell_order(
            db, test_user, grams=9999.0, withdrawal_crypto="USDT", withdrawal_wallet="TxxxxWallet"
        )


@pytest.mark.asyncio
async def test_sell_reserves_gold(db: AsyncSession, test_user: User):
    from unittest.mock import AsyncMock, patch

    from app.services.order_service import create_sell_order

    initial_gold = test_user.gold_grams
    grams_to_sell = 10.0

    with patch("app.services.order_service.get_gold_price", new_callable=AsyncMock) as mock_price:
        from app.services.price_service import GoldPriceData
        import time
        mock_price.return_value = GoldPriceData(
            price_per_oz_usd=2480.0,
            price_per_gram_usd=79.73,
            aed_usd_rate=0.272,
            timestamp=time.time(),
        )
        order = await create_sell_order(
            db, test_user, grams=grams_to_sell,
            withdrawal_crypto="USDT", withdrawal_wallet="TxxxxWalletAddress123"
        )

    assert order.order_type == OrderType.SELL
    assert order.status == OrderStatus.PENDING
    assert order.grams == grams_to_sell
    assert test_user.gold_grams == pytest.approx(initial_gold - grams_to_sell)


@pytest.mark.asyncio
async def test_user_creation(db: AsyncSession):
    user, created = await get_or_create_user(
        db, telegram_id=111222333, username="newtrader", first_name="Gold"
    )
    assert created is True
    assert user.telegram_id == 111222333
    assert user.referral_code.startswith("GV-")

    user2, created2 = await get_or_create_user(db, telegram_id=111222333)
    assert created2 is False
    assert user2.id == user.id
