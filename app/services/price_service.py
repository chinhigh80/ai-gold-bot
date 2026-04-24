"""Gold price fetching, caching, and calculation engine."""
from __future__ import annotations

import json
import time

import httpx
import structlog

from app.config import settings
from app.db.redis import redis_get, redis_set

logger = structlog.get_logger(__name__)

PRICE_CACHE_KEY = "gold:price:current"
IMAGE_CACHE_KEY = "gold:image:luxury"

GOLD_API_URL = "https://www.goldapi.io/api/XAU/USD"
_EXCHANGE_RATE_BASE = "https://v6.exchangerate-api.com/v6"
_SWISSQUOTE_URL = "https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XAU/USD"


async def _cfg(key: str, default: str) -> str:
    """Read a string setting from Redis (admin panel), fall back to .env value."""
    val = await redis_get(f"admin:cfg:{key}")
    return val.strip() if val else default


class GoldPriceData:
    __slots__ = (
        "price_per_oz_usd",
        "price_per_gram_usd",
        "aed_usd_rate",
        "timestamp",
        "source",
    )

    def __init__(
        self,
        price_per_oz_usd: float,
        price_per_gram_usd: float,
        aed_usd_rate: float,
        timestamp: float,
        source: str = "goldapi",
    ) -> None:
        self.price_per_oz_usd = price_per_oz_usd
        self.price_per_gram_usd = price_per_gram_usd
        self.aed_usd_rate = aed_usd_rate
        self.timestamp = timestamp
        self.source = source

    def to_dict(self) -> dict:
        return {
            "price_per_oz_usd": self.price_per_oz_usd,
            "price_per_gram_usd": self.price_per_gram_usd,
            "aed_usd_rate": self.aed_usd_rate,
            "timestamp": self.timestamp,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GoldPriceData":
        return cls(**data)


async def _fetch_from_goldapi(gold_api_key: str) -> float:
    """Fetch XAU/USD spot price (per troy oz) from GoldAPI.io. Returns price_per_oz."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        headers = {"x-access-token": gold_api_key, "Content-Type": "application/json"}
        response = await client.get(GOLD_API_URL, headers=headers)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise ValueError(f"GoldAPI error: {data['error']}")
        return float(data["price"])


async def _fetch_from_swissquote() -> float:
    """
    Fetch XAU/USD spot price (per troy oz) from Swissquote public feed.
    Free, no API key required. Uses mid-price of the first server's premium spread.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(_SWISSQUOTE_URL, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        data = response.json()
    # data is a list of servers; pick first server's first spread profile
    spread = data[0]["spreadProfilePrices"][0]
    mid = (float(spread["bid"]) + float(spread["ask"])) / 2
    return mid


async def _fetch_gold_price_from_api() -> GoldPriceData:
    """
    Fetch gold price. Tries GoldAPI.io first (if key configured), then falls
    back to Swissquote free public feed. Either way returns a GoldPriceData.
    """
    gold_api_key = await _cfg("GOLD_API_KEY", settings.GOLD_API_KEY)
    exc_rate_key = await _cfg("EXCHANGE_RATE_API_KEY", settings.EXCHANGE_RATE_API_KEY)

    source = "goldapi"
    price_per_oz: float | None = None

    # --- Primary: GoldAPI.io (requires API key) ---
    if gold_api_key:
        try:
            price_per_oz = await _fetch_from_goldapi(gold_api_key)
            source = "goldapi"
        except Exception as exc:
            logger.warning("goldapi_fetch_failed", error=str(exc), fallback="swissquote")

    # --- Fallback: Swissquote free feed (no key needed) ---
    if price_per_oz is None:
        try:
            price_per_oz = await _fetch_from_swissquote()
            source = "swissquote"
        except Exception as exc:
            logger.error("swissquote_fetch_failed", error=str(exc))

    if price_per_oz is None:
        raise RuntimeError("All gold price sources failed. Check API keys and network.")

    price_per_gram = price_per_oz / settings.TROY_OUNCE_TO_GRAM
    aed_usd_rate = await _fetch_aed_usd_rate(exc_rate_key)

    return GoldPriceData(
        price_per_oz_usd=price_per_oz,
        price_per_gram_usd=price_per_gram,
        aed_usd_rate=aed_usd_rate,
        timestamp=time.time(),
        source=source,
    )


async def _fetch_aed_usd_rate(exc_rate_key: str = "") -> float:
    """Fetch AED to USD exchange rate. Returns ~0.272 typically."""
    key = exc_rate_key or settings.EXCHANGE_RATE_API_KEY
    try:
        url = f"{_EXCHANGE_RATE_BASE}/{key}/pair/AED/USD"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return float(resp.json()["conversion_rate"])
    except Exception:
        logger.warning("aed_usd_fetch_failed", fallback=0.272)
        return 0.272


async def get_gold_price() -> GoldPriceData:
    """Get gold price, using Redis cache when fresh."""
    cached = await redis_get(PRICE_CACHE_KEY)
    if cached:
        try:
            data = json.loads(cached)
            logger.debug("gold_price_from_cache", price=data["price_per_gram_usd"])
            return GoldPriceData.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            pass

    price_data = await _fetch_gold_price_from_api()
    await redis_set(
        PRICE_CACHE_KEY,
        json.dumps(price_data.to_dict()),
        ttl=settings.PRICE_CACHE_TTL,
    )
    logger.info(
        "gold_price_fetched",
        price_per_oz=price_data.price_per_oz_usd,
        price_per_gram=price_data.price_per_gram_usd,
        source=price_data.source,
    )
    return price_data


async def _admin_setting(key: str, default: float) -> float:
    """Read a setting from Redis (set by admin dashboard), fall back to config."""
    from app.db.redis import redis_get
    val = await redis_get(f"admin:cfg:{key}")
    try:
        return float(val) if val else default
    except (TypeError, ValueError):
        return default


async def calculate_buy_price_async(
    price_per_gram_usd: float,
    grams: float,
    markup_percent: float | None = None,
) -> dict:
    markup = markup_percent if markup_percent is not None else await _admin_setting("markup_percent", settings.MARKUP_PERCENT)
    marked_price = price_per_gram_usd * (1 + markup / 100)
    return {
        "base_price_per_gram_usd": price_per_gram_usd,
        "price_per_gram_usd": round(marked_price, 4),
        "grams": grams,
        "total_usd": round(marked_price * grams, 2),
        "markup_percent": markup,
    }


async def calculate_sell_price_async(
    price_per_gram_usd: float,
    grams: float,
    spread_percent: float | None = None,
) -> dict:
    spread = spread_percent if spread_percent is not None else await _admin_setting("spread_percent", settings.SPREAD_PERCENT)
    net_price = price_per_gram_usd * (1 - spread / 100)
    return {
        "base_price_per_gram_usd": price_per_gram_usd,
        "price_per_gram_usd": round(net_price, 4),
        "grams": grams,
        "total_usd": round(net_price * grams, 2),
        "spread_percent": spread,
    }


def calculate_buy_price(
    price_per_gram_usd: float,
    grams: float,
    markup_percent: float | None = None,
) -> dict:
    markup = markup_percent if markup_percent is not None else settings.MARKUP_PERCENT
    marked_price = price_per_gram_usd * (1 + markup / 100)
    return {
        "base_price_per_gram_usd": price_per_gram_usd,
        "price_per_gram_usd": round(marked_price, 4),
        "grams": grams,
        "total_usd": round(marked_price * grams, 2),
        "markup_percent": markup,
    }


def calculate_sell_price(
    price_per_gram_usd: float,
    grams: float,
    spread_percent: float | None = None,
) -> dict:
    spread = spread_percent if spread_percent is not None else settings.SPREAD_PERCENT
    net_price = price_per_gram_usd * (1 - spread / 100)
    return {
        "base_price_per_gram_usd": price_per_gram_usd,
        "price_per_gram_usd": round(net_price, 4),
        "grams": grams,
        "total_usd": round(net_price * grams, 2),
        "spread_percent": spread,
    }
