from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # App
    APP_NAME: str = "GoldVault"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "production"
    DEBUG: bool = False
    SECRET_KEY: str = secrets.token_urlsafe(32)

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://gold_user:gold_pass@db:5432/gold_db"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # Telegram Bot
    BOT_TOKEN: str = ""
    WEBHOOK_HOST: Optional[str] = None
    WEBHOOK_PATH: str = "/bot/webhook"
    WEBHOOK_SECRET: Optional[str] = None

    # Price APIs
    GOLD_API_KEY: str = ""
    METALS_API_KEY: Optional[str] = None
    EXCHANGE_RATE_API_KEY: str = ""

    # NOWPayments
    NOWPAYMENTS_API_KEY: str = ""
    NOWPAYMENTS_IPN_SECRET: str = ""
    NOWPAYMENTS_CALLBACK_URL: str = ""
    NOWPAYMENTS_BASE_URL: str = "https://api.nowpayments.io/v1"

    # Unsplash
    UNSPLASH_ACCESS_KEY: str = ""
    UNSPLASH_BASE_URL: str = "https://api.unsplash.com"

    # Business Logic
    MARKUP_PERCENT: float = 2.5
    SPREAD_PERCENT: float = 1.5
    PRICE_CACHE_TTL: int = 60       # seconds
    PRICE_LOCK_DURATION: int = 300  # 5 minutes
    REFERRAL_BONUS_PERCENT: float = 1.0
    MIN_BUY_GRAMS: float = 0.1
    MAX_BUY_GRAMS: float = 999_999_999.0  # Effectively unlimited
    MIN_SELL_GRAMS: float = 0.1
    TROY_OUNCE_TO_GRAM: float = 31.1035

    # Admin Panel
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "changeme"
    JWT_SECRET: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 30

    # Admin Notifications (comma-separated Telegram IDs)
    ADMIN_TELEGRAM_IDS: str = ""

    # Supported assets
    SUPPORTED_CRYPTOS: str = "BTC,ETH,USDT"
    BASE_CURRENCY: str = "USD"

    @property
    def admin_telegram_ids(self) -> list[int]:
        if not self.ADMIN_TELEGRAM_IDS:
            return []
        return [int(x.strip()) for x in self.ADMIN_TELEGRAM_IDS.split(",") if x.strip().isdigit()]

    @property
    def supported_cryptos(self) -> list[str]:
        return [x.strip().upper() for x in self.SUPPORTED_CRYPTOS.split(",") if x.strip()]

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def webhook_url(self) -> Optional[str]:
        if self.WEBHOOK_HOST:
            return f"{self.WEBHOOK_HOST}{self.WEBHOOK_PATH}"
        return None


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
