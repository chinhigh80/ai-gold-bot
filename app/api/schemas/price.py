from datetime import datetime

from pydantic import BaseModel


class GoldPriceResponse(BaseModel):
    price_per_oz_usd: float
    price_per_gram_usd: float
    buy_price_per_gram_usd: float   # with markup
    sell_price_per_gram_usd: float  # with spread
    aed_usd_rate: float
    markup_percent: float
    spread_percent: float
    cached_at: float
    source: str
