from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: str = "en"
    referral_code: Optional[str] = None


class UserUpdate(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    language_code: str
    balance_usd: float
    gold_grams: float
    referral_code: str
    referral_bonus_earned_usd: float
    is_active: bool
    is_banned: bool
    created_at: datetime


class WalletResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    telegram_id: int
    display_name: str
    balance_usd: float
    gold_grams: float
    gold_value_usd: float
    referral_code: str
    referral_bonus_earned_usd: float
