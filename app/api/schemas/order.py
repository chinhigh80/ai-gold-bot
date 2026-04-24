from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.order import OrderStatus, OrderType


class BuyOrderRequest(BaseModel):
    telegram_id: int
    grams: float = Field(..., gt=0, le=10000)
    crypto_currency: str = Field(default="USDT", pattern=r"^(BTC|ETH|USDT|USDC)$")

    @field_validator("grams")
    @classmethod
    def validate_grams(cls, v: float) -> float:
        if v < 0.1:
            raise ValueError("Minimum purchase is 0.1 grams")
        return round(v, 4)


class SellOrderRequest(BaseModel):
    telegram_id: int
    grams: float = Field(..., gt=0)
    withdrawal_crypto: str = Field(..., pattern=r"^(BTC|ETH|USDT)$")
    withdrawal_wallet: str = Field(..., min_length=10, max_length=200)

    @field_validator("grams")
    @classmethod
    def validate_grams(cls, v: float) -> float:
        if v < 0.1:
            raise ValueError("Minimum sell is 0.1 grams")
        return round(v, 4)


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    order_type: OrderType
    grams: float
    price_per_gram_usd: float
    base_price_per_gram_usd: float
    total_usd: float
    markup_percent: float
    spread_percent: float
    status: OrderStatus
    payment_id: Optional[str]
    payment_url: Optional[str]
    payment_address: Optional[str]
    crypto_currency: Optional[str]
    crypto_amount: Optional[float]
    withdrawal_crypto: Optional[str]
    withdrawal_wallet: Optional[str]
    created_at: datetime


class PriceQuote(BaseModel):
    grams: float
    base_price_per_gram_usd: float
    price_per_gram_usd: float
    total_usd: float
    markup_percent: float
    spread_percent: float
    valid_for_seconds: int
    quote_type: str  # "buy" or "sell"
