"""NOWPayments crypto payment integration."""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Optional

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


async def _cfg(key: str, default: str) -> str:
    """Read a string setting from Redis (admin panel), fall back to .env value."""
    from app.db.redis import redis_get
    val = await redis_get(f"admin:cfg:{key}")
    return val.strip() if val else default


NOWPAYMENTS_BASE = settings.NOWPAYMENTS_BASE_URL

# Map our currency names to NOWPayments pay_currency codes
CRYPTO_CURRENCY_MAP = {
    "BTC": "btc",
    "ETH": "eth",
    "USDT": "usdttrc20",
    "USDC": "usdcerc20",
    "BNB": "bnbbsc",
    "SOL": "sol",
    "MATIC": "maticpolygon",
    "TRX": "trx",
    "LTC": "ltc",
    "DOGE": "doge",
    "XRP": "xrp",
    "ADA": "ada",
}


class PaymentInvoice:
    __slots__ = (
        "payment_id",
        "payment_url",
        "payment_address",
        "pay_amount",
        "pay_currency",
        "price_amount",
        "price_currency",
        "status",
    )

    def __init__(self, data: dict) -> None:
        self.payment_id      = str(data.get("payment_id", ""))
        self.payment_url     = data.get("invoice_url") or data.get("payment_url", "")
        self.payment_address = data.get("pay_address", "")
        self.pay_amount      = float(data.get("pay_amount", 0))
        self.pay_currency    = data.get("pay_currency", "")
        self.price_amount    = float(data.get("price_amount", 0))
        self.price_currency  = data.get("price_currency", "USD")
        self.status          = data.get("payment_status", "waiting")


async def create_payment(
    amount_usd: float,
    crypto_currency: str,
    order_id: int,
    description: str = "Gold Purchase - GoldVault",
) -> PaymentInvoice:
    """Create a crypto payment invoice via NOWPayments."""
    api_key      = await _cfg("NOWPAYMENTS_API_KEY",      settings.NOWPAYMENTS_API_KEY)
    callback_url = await _cfg("NOWPAYMENTS_CALLBACK_URL", settings.NOWPAYMENTS_CALLBACK_URL)

    pay_currency = CRYPTO_CURRENCY_MAP.get(crypto_currency.upper(), "usdttrc20")

    payload = {
        "price_amount":      amount_usd,
        "price_currency":    "usd",
        "pay_currency":      pay_currency,
        "order_id":          str(order_id),
        "order_description": description,
        "ipn_callback_url":  callback_url,
        "is_fee_paid_by_user": False,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{NOWPAYMENTS_BASE}/payment",
            json=payload,
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()

    invoice = PaymentInvoice(data)
    logger.info(
        "payment_created",
        payment_id=invoice.payment_id,
        order_id=order_id,
        amount_usd=amount_usd,
        currency=crypto_currency,
    )
    return invoice


async def get_payment_status(payment_id: str) -> dict:
    api_key = await _cfg("NOWPAYMENTS_API_KEY", settings.NOWPAYMENTS_API_KEY)
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{NOWPAYMENTS_BASE}/payment/{payment_id}",
            headers={"x-api-key": api_key},
        )
        response.raise_for_status()
        return response.json()


def verify_ipn_signature(payload: bytes, received_sig: str, secret: str = "") -> bool:
    """Verify IPN webhook signature. Pass `secret` explicitly (read from Redis by caller)."""
    ipn_secret = secret or settings.NOWPAYMENTS_IPN_SECRET
    expected = hmac.new(
        ipn_secret.encode(),
        payload,
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(expected, received_sig)


def is_payment_confirmed(status: str) -> bool:
    return status in {"finished", "confirmed", "partially_paid"}


def is_payment_failed(status: str) -> bool:
    return status in {"failed", "refunded", "expired"}


async def get_available_currencies() -> list[str]:
    api_key = await _cfg("NOWPAYMENTS_API_KEY", settings.NOWPAYMENTS_API_KEY)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{NOWPAYMENTS_BASE}/currencies",
            headers={"x-api-key": api_key},
        )
        resp.raise_for_status()
        data = resp.json()
    return data.get("currencies", [])
