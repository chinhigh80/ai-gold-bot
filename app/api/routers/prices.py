from fastapi import APIRouter, HTTPException

from app.api.schemas.price import GoldPriceResponse
from app.config import settings
from app.services.price_service import calculate_buy_price, calculate_sell_price, get_gold_price

router = APIRouter()


@router.get("/current", response_model=GoldPriceResponse, summary="Get current gold price")
async def get_current_price():
    """Fetch current gold price with buy/sell rates applied."""
    try:
        price_data = await get_gold_price()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    buy_calc = calculate_buy_price(price_data.price_per_gram_usd, 1.0)
    sell_calc = calculate_sell_price(price_data.price_per_gram_usd, 1.0)

    return GoldPriceResponse(
        price_per_oz_usd=price_data.price_per_oz_usd,
        price_per_gram_usd=price_data.price_per_gram_usd,
        buy_price_per_gram_usd=buy_calc["price_per_gram_usd"],
        sell_price_per_gram_usd=sell_calc["price_per_gram_usd"],
        aed_usd_rate=price_data.aed_usd_rate,
        markup_percent=settings.MARKUP_PERCENT,
        spread_percent=settings.SPREAD_PERCENT,
        cached_at=price_data.timestamp,
        source=price_data.source,
    )


@router.get("/quote/buy", summary="Get buy price quote")
async def get_buy_quote(grams: float = 1.0):
    if grams <= 0:
        raise HTTPException(status_code=400, detail="Grams must be positive")
    try:
        price_data = await get_gold_price()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    return calculate_buy_price(price_data.price_per_gram_usd, grams)


@router.get("/quote/sell", summary="Get sell price quote")
async def get_sell_quote(grams: float = 1.0):
    if grams <= 0:
        raise HTTPException(status_code=400, detail="Grams must be positive")
    try:
        price_data = await get_gold_price()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    return calculate_sell_price(price_data.price_per_gram_usd, grams)
