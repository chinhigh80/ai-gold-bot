from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.withdrawal import WithdrawalStatus


class WithdrawalRequest(BaseModel):
    telegram_id: int
    grams: float = Field(..., gt=0)
    crypto_type: str = Field(..., pattern=r"^(BTC|ETH|USDT)$")
    wallet_address: str = Field(..., min_length=10, max_length=200)

    @field_validator("wallet_address")
    @classmethod
    def sanitize_wallet(cls, v: str) -> str:
        return v.strip()


class WithdrawalAdminAction(BaseModel):
    action: str = Field(..., pattern=r"^(approve|reject|complete)$")
    admin_notes: Optional[str] = None
    tx_hash: Optional[str] = None


class WithdrawalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    amount_usd: float
    gold_grams: float
    crypto_type: str
    wallet_address: str
    crypto_amount: Optional[float]
    gold_price_per_gram_usd: float
    spread_percent: float
    status: WithdrawalStatus
    admin_notes: Optional[str]
    tx_hash: Optional[str]
    created_at: datetime
