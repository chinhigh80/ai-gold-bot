"""FastAPI dependency injection."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db


# ── Database ──────────────────────────────────────────────────────────────────

DbSession = Annotated[AsyncSession, Depends(get_db)]


# ── Bot-to-API internal auth ──────────────────────────────────────────────────

async def verify_bot_token(x_bot_secret: str = Header(...)) -> None:
    """Simple shared secret auth for bot→API calls."""
    if x_bot_secret != settings.SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bot secret",
        )


BotAuth = Annotated[None, Depends(verify_bot_token)]


# ── Admin JWT auth ─────────────────────────────────────────────────────────────

def _decode_admin_token(token: str) -> dict:
    from jose import JWTError, jwt

    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from e


async def get_current_admin(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")
    token = authorization.split(" ", 1)[1]
    return _decode_admin_token(token)


AdminAuth = Annotated[dict, Depends(get_current_admin)]
