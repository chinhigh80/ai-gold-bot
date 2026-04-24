"""Integration tests for price API endpoints."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import time

from app.services.price_service import GoldPriceData


def _mock_price():
    return GoldPriceData(
        price_per_oz_usd=2480.0,
        price_per_gram_usd=79.73,
        aed_usd_rate=0.272,
        timestamp=time.time(),
        source="goldapi",
    )


@pytest.mark.asyncio
async def test_get_current_price(client):
    with patch("app.api.routers.prices.get_gold_price", new_callable=AsyncMock) as mock:
        mock.return_value = _mock_price()
        resp = await client.get("/api/v1/prices/current")

    assert resp.status_code == 200
    data = resp.json()
    assert "price_per_gram_usd" in data
    assert "buy_price_per_gram_usd" in data
    assert "sell_price_per_gram_usd" in data
    assert data["buy_price_per_gram_usd"] > data["price_per_gram_usd"]
    assert data["sell_price_per_gram_usd"] < data["price_per_gram_usd"]


@pytest.mark.asyncio
async def test_buy_quote(client):
    with patch("app.api.routers.prices.get_gold_price", new_callable=AsyncMock) as mock:
        mock.return_value = _mock_price()
        resp = await client.get("/api/v1/prices/quote/buy?grams=5")

    assert resp.status_code == 200
    data = resp.json()
    assert data["grams"] == 5.0
    assert data["total_usd"] > 0


@pytest.mark.asyncio
async def test_sell_quote(client):
    with patch("app.api.routers.prices.get_gold_price", new_callable=AsyncMock) as mock:
        mock.return_value = _mock_price()
        resp = await client.get("/api/v1/prices/quote/sell?grams=5")

    assert resp.status_code == 200
    data = resp.json()
    assert data["grams"] == 5.0
    assert data["total_usd"] > 0


@pytest.mark.asyncio
async def test_invalid_grams(client):
    resp = await client.get("/api/v1/prices/quote/buy?grams=-1")
    assert resp.status_code == 400
