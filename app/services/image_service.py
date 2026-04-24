"""Gold image service — no API key required.

Three-tier delivery:
  1. Cached Telegram file_id (Redis) — instant, always works once seeded
  2. Downloaded bytes sent directly — bot fetches URL locally (Docker can reach Unsplash)
     then uploads bytes to Telegram, bypassing Telegram's own URL-fetching which can fail
  3. Raw URL string — last-resort fallback
"""
from __future__ import annotations

import httpx
import structlog
from aiogram.types import BufferedInputFile

from app.db.redis import redis_get, redis_set

logger = structlog.get_logger(__name__)

_BASE = "https://images.unsplash.com/"
# All contexts use the same confirmed-working gold bullion photo.
# After first upload Telegram gives us a stable file_id cached per context.
GOLD_IMAGES: dict[str, str] = {
    "welcome":      _BASE + "photo-1610375461246-83df859d849d?w=1280&q=85&fit=crop",
    "buy":          _BASE + "photo-1610375461246-83df859d849d?w=1280&q=85&fit=crop",
    "sell":         _BASE + "photo-1610375461246-83df859d849d?w=1280&q=85&fit=crop",
    "wallet":       _BASE + "photo-1610375461246-83df859d849d?w=1280&q=85&fit=crop",
    "referral":     _BASE + "photo-1610375461246-83df859d849d?w=1280&q=85&fit=crop",
    "support":      _BASE + "photo-1610375461246-83df859d849d?w=1280&q=85&fit=crop",
    "transactions": _BASE + "photo-1610375461246-83df859d849d?w=1280&q=85&fit=crop",
    "default":      _BASE + "photo-1610375461246-83df859d849d?w=1280&q=85&fit=crop",
}

_REDIS_PREFIX = "gold:photo:file_id:"


async def get_gold_photo_input(context: str = "default"):
    """
    Return the best available photo reference for aiogram's answer_photo().

    Priority:
      1. Admin-set welcome photo (only for context="welcome")
      2. Cached Telegram file_id from Redis
      3. Image bytes downloaded locally (reliable — Docker CAN reach Unsplash)
      4. URL string (last resort)
    """
    # Admin-overridden welcome image takes top priority
    if context == "welcome":
        admin_val = await redis_get("admin:cfg:welcome_photo_url")
        if admin_val == "__file__":
            import base64
            b64 = await redis_get("admin:cfg:welcome_photo_bytes")
            if b64:
                return BufferedInputFile(base64.b64decode(b64), filename="welcome.jpg")
        elif admin_val:
            if admin_val.startswith("http"):
                # Download bytes locally so Telegram receives bytes directly (reliable)
                try:
                    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                        r = await client.get(admin_val, headers={"User-Agent": "Mozilla/5.0"})
                        if r.status_code == 200 and r.content:
                            return BufferedInputFile(r.content, filename="welcome.jpg")
                except Exception as exc:
                    logger.warning("welcome_image_url_download_failed", url=admin_val[:80], error=str(exc))
            return admin_val  # Telegram file_id (instant) or URL last resort

    # Cached file_id — instant delivery
    cached = await redis_get(_REDIS_PREFIX + context)
    if cached:
        return cached

    url = GOLD_IMAGES.get(context, GOLD_IMAGES["default"])

    # Download bytes locally so Telegram gets bytes directly (most reliable)
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200 and r.content:
                logger.debug("gold_image_downloaded", context=context, bytes=len(r.content))
                return BufferedInputFile(r.content, filename="gold.jpg")
    except Exception as exc:
        logger.warning("gold_image_download_failed", context=context, url=url, error=str(exc))

    # Last resort: let Telegram try to fetch the URL itself
    return url


async def get_gold_photo(context: str = "default") -> str:
    """Return cached Telegram file_id if available, else the image URL (string only)."""
    cached = await redis_get(_REDIS_PREFIX + context)
    if cached:
        return cached
    return GOLD_IMAGES.get(context, GOLD_IMAGES["default"])


async def cache_photo_file_id(context: str, file_id: str) -> None:
    """Persist Telegram file_id after first upload (permanent cache)."""
    await redis_set(_REDIS_PREFIX + context, file_id)
    logger.debug("gold_photo_cached", context=context)


def get_photo_url(context: str = "default") -> str:
    """Synchronous URL lookup (no Redis) — for startup/fallback use."""
    return GOLD_IMAGES.get(context, GOLD_IMAGES["default"])
