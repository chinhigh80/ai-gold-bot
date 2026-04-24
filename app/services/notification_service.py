"""Admin and user Telegram notification service.

Uses httpx directly (no aiogram dependency) so it works in both
the bot process and the API/Celery processes.
"""
from __future__ import annotations

import structlog
import httpx

from app.config import settings

logger = structlog.get_logger(__name__)

_TG_BASE = f"https://api.telegram.org/bot{settings.BOT_TOKEN}"


async def _send_message(chat_id: int, text: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{_TG_BASE}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            )
            return r.status_code == 200
    except Exception as e:
        logger.warning("telegram_send_failed", chat_id=chat_id, error=str(e))
        return False


async def _send_photo(chat_id: int, photo: str, caption: str = "") -> bool:
    """Send a photo (URL or file_id) with optional caption."""
    try:
        payload: dict = {"chat_id": chat_id, "photo": photo, "parse_mode": "HTML"}
        if caption:
            payload["caption"] = caption
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{_TG_BASE}/sendPhoto", json=payload)
            return r.status_code == 200
    except Exception as e:
        logger.warning("telegram_send_photo_failed", chat_id=chat_id, error=str(e))
        return False


async def upload_photo_bytes(photo_bytes: bytes, filename: str, chat_id: int) -> str | None:
    """
    Upload raw image bytes to Telegram, return the stable file_id.
    Sends to `chat_id` (typically an admin) once to obtain a reusable file_id.
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{_TG_BASE}/sendPhoto",
                data={"chat_id": chat_id, "parse_mode": "HTML"},
                files={"photo": (filename, photo_bytes, "image/jpeg")},
            )
            if r.status_code == 200:
                result = r.json().get("result", {})
                photos = result.get("photo", [])
                if photos:
                    file_id = photos[-1]["file_id"]
                    logger.info("photo_uploaded", file_id=file_id[:20])
                    return file_id
            logger.warning("upload_photo_failed", status=r.status_code, body=r.text[:200])
    except Exception as e:
        logger.warning("upload_photo_exception", error=str(e))
    return None


async def notify_admins(message: str) -> None:
    """Send a message to all configured admin Telegram IDs."""
    for admin_id in settings.admin_telegram_ids:
        await _send_message(admin_id, message)


async def notify_user(telegram_id: int, message: str) -> None:
    """Send a notification to a specific user."""
    await _send_message(telegram_id, message)


async def broadcast_message(telegram_ids: list[int], message: str) -> dict:
    """Broadcast a text-only message to a list of Telegram user IDs."""
    success = 0
    failed  = 0
    async with httpx.AsyncClient(timeout=10) as client:
        for tid in telegram_ids:
            try:
                r = await client.post(
                    f"{_TG_BASE}/sendMessage",
                    json={"chat_id": tid, "text": message, "parse_mode": "HTML"},
                )
                if r.status_code == 200:
                    success += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
    logger.info("broadcast_complete", success=success, failed=failed)
    return {"success": success, "failed": failed}


async def broadcast_photo_message(
    telegram_ids: list[int],
    photo: str,
    caption: str = "",
) -> dict:
    """Broadcast a photo (URL or file_id) with optional caption."""
    success = 0
    failed  = 0
    async with httpx.AsyncClient(timeout=15) as client:
        for tid in telegram_ids:
            try:
                payload: dict = {
                    "chat_id": tid,
                    "photo": photo,
                    "parse_mode": "HTML",
                }
                if caption:
                    payload["caption"] = caption
                r = await client.post(f"{_TG_BASE}/sendPhoto", json=payload)
                if r.status_code == 200:
                    success += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
    logger.info("broadcast_photo_complete", success=success, failed=failed)
    return {"success": success, "failed": failed}
