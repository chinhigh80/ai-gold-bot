"""Unit tests for price calculation logic (no external API calls)."""
import pytest

from app.services.price_service import calculate_buy_price, calculate_sell_price


class TestBuyPriceCalculation:
    def test_basic_markup(self):
        result = calculate_buy_price(price_per_gram_usd=80.0, grams=1.0, markup_percent=2.5)
        assert result["price_per_gram_usd"] == pytest.approx(82.0, rel=1e-4)
        assert result["total_usd"] == pytest.approx(82.0, rel=1e-4)
        assert result["markup_percent"] == 2.5

    def test_multi_gram(self):
        result = calculate_buy_price(price_per_gram_usd=80.0, grams=10.0, markup_percent=2.5)
        assert result["total_usd"] == pytest.approx(820.0, rel=1e-3)
        assert result["grams"] == 10.0

    def test_zero_markup(self):
        result = calculate_buy_price(price_per_gram_usd=80.0, grams=5.0, markup_percent=0.0)
        assert result["price_per_gram_usd"] == pytest.approx(80.0)
        assert result["total_usd"] == pytest.approx(400.0)

    def test_base_price_preserved(self):
        result = calculate_buy_price(price_per_gram_usd=80.0, grams=1.0, markup_percent=5.0)
        assert result["base_price_per_gram_usd"] == 80.0
        assert result["price_per_gram_usd"] > result["base_price_per_gram_usd"]

    def test_uses_default_markup_when_none(self):
        from app.config import settings
        result = calculate_buy_price(price_per_gram_usd=80.0, grams=1.0)
        assert result["markup_percent"] == settings.MARKUP_PERCENT


class TestSellPriceCalculation:
    def test_basic_spread(self):
        result = calculate_sell_price(price_per_gram_usd=80.0, grams=1.0, spread_percent=1.5)
        assert result["price_per_gram_usd"] == pytest.approx(78.8, rel=1e-3)
        assert result["total_usd"] == pytest.approx(78.8, rel=1e-3)

    def test_sell_less_than_buy(self):
        buy = calculate_buy_price(price_per_gram_usd=80.0, grams=1.0, markup_percent=2.5)
        sell = calculate_sell_price(price_per_gram_usd=80.0, grams=1.0, spread_percent=1.5)
        assert sell["total_usd"] < buy["total_usd"]

    def test_spread_applied(self):
        result = calculate_sell_price(price_per_gram_usd=100.0, grams=1.0, spread_percent=2.0)
        assert result["price_per_gram_usd"] == pytest.approx(98.0)

    def test_total_proportional_to_grams(self):
        r1 = calculate_sell_price(80.0, 1.0, 1.5)
        r5 = calculate_sell_price(80.0, 5.0, 1.5)
        assert r5["total_usd"] == pytest.approx(r1["total_usd"] * 5, rel=1e-5)
