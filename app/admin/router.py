"""Admin panel routes using Jinja2 templates."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from typing import Optional
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.auth import create_access_token, decode_access_token, verify_password
from app.config import settings
from app.db.session import get_db
from app.db.redis import redis_get, redis_set
from app.models.admin_user import AdminUser
from app.models.order import Order, OrderStatus, OrderType
from app.models.user import User
from app.models.withdrawal import Withdrawal, WithdrawalStatus

router = APIRouter()
templates = Jinja2Templates(directory="app/admin/templates")


@router.get("/", include_in_schema=False)
async def admin_root():
    return RedirectResponse(url="/admin/login", status_code=302)


# ── Auth helpers ───────────────────────────────────────────────────────────────

def _require_admin(request: Request) -> dict:
    token = request.cookies.get("admin_token")
    if not token:
        return None
    return decode_access_token(token)


async def _get_admin_user(request: Request, db: AsyncSession) -> AdminUser | None:
    payload = _require_admin(request)
    if not payload:
        return None
    result = await db.execute(
        select(AdminUser).where(AdminUser.username == payload.get("sub"))
    )
    return result.scalar_one_or_none()


# ── Redis-backed settings helpers ─────────────────────────────────────────────

async def _get_setting(key: str, default: float) -> float:
    val = await redis_get(f"admin:cfg:{key}")
    try:
        return float(val) if val else default
    except (TypeError, ValueError):
        return default


async def _save_setting(key: str, value: float) -> None:
    await redis_set(f"admin:cfg:{key}", str(value))


async def _get_str(key: str, default: str = "") -> str:
    val = await redis_get(f"admin:cfg:{key}")
    return val if val is not None else default


async def _save_str(key: str, value: str) -> None:
    await redis_set(f"admin:cfg:{key}", value.strip())


# ── Login ─────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
async def admin_login(
    request: Request,
    db: AsyncSession = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
):
    result = await db.execute(select(AdminUser).where(AdminUser.username == username))
    admin = result.scalar_one_or_none()

    if not admin or not verify_password(password, admin.hashed_password):
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Invalid credentials"}
        )

    token = create_access_token({"sub": admin.username})
    response = RedirectResponse(url="/admin/dashboard", status_code=302)
    response.set_cookie("admin_token", token, httponly=True, samesite="lax", max_age=86400)
    return response


@router.get("/logout")
async def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("admin_token")
    return response


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    admin = await _get_admin_user(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    total_users   = (await db.execute(select(func.count(User.id)))).scalar_one()
    total_orders  = (await db.execute(select(func.count(Order.id)))).scalar_one()

    # Use .value to avoid asyncpg Python 3.11 enum name bug
    pending_withdrawals = (
        await db.execute(
            select(func.count(Withdrawal.id)).where(
                Withdrawal.status == WithdrawalStatus.PENDING.value
            )
        )
    ).scalar_one()

    revenue_result = await db.execute(
        select(func.sum(Order.total_usd)).where(
            Order.status == OrderStatus.COMPLETED.value,
            Order.order_type == OrderType.BUY.value,
        )
    )
    total_revenue = float(revenue_result.scalar_one() or 0)

    # Pending receipt orders (status = PAID, has RECEIPT in admin_notes)
    from sqlalchemy import and_
    receipt_result = await db.execute(
        select(Order).where(
            and_(
                Order.status == OrderStatus.PAID.value,
                Order.admin_notes.like("RECEIPT:%"),
            )
        ).order_by(Order.created_at.desc()).limit(20)
    )
    pending_receipts = list(receipt_result.scalars().all())

    recent_orders_result = await db.execute(
        select(Order).order_by(Order.created_at.desc()).limit(10)
    )
    recent_orders = list(recent_orders_result.scalars().all())

    price_source = ""
    price_error = ""
    try:
        from app.services.price_service import get_gold_price
        price_data    = await get_gold_price()
        current_price = price_data.price_per_gram_usd
        price_source  = price_data.source
    except Exception as e:
        current_price = 0.0
        price_error   = str(e)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "admin": admin,
            "total_users": total_users,
            "total_orders": total_orders,
            "pending_withdrawals": pending_withdrawals,
            "total_revenue": total_revenue,
            "recent_orders": recent_orders,
            "pending_receipts": pending_receipts,
            "current_price": current_price,
            "price_source": price_source,
            "price_error": price_error,
        },
    )


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users", response_class=HTMLResponse)
async def users_list(request: Request, db: AsyncSession = Depends(get_db), page: int = 1):
    admin = await _get_admin_user(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    per_page = 50
    offset   = (page - 1) * per_page
    result   = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(per_page)
    )
    users = result.scalars().all()
    total = (await db.execute(select(func.count(User.id)))).scalar_one()

    return templates.TemplateResponse(
        "users.html",
        {"request": request, "admin": admin, "users": users, "page": page,
         "total": total, "per_page": per_page},
    )


@router.post("/users/{user_id}/ban")
async def ban_user(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    admin = await _get_admin_user(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.is_banned = not user.is_banned
        await db.commit()
    return RedirectResponse(url="/admin/users", status_code=302)


@router.post("/users/{user_id}/credit")
async def credit_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    gold_grams: float = Form(0.0),
    balance_usd: float = Form(0.0),
):
    admin = await _get_admin_user(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.gold_grams  = round(user.gold_grams + gold_grams, 8)
        user.balance_usd = round(user.balance_usd + balance_usd, 2)
        await db.commit()
    return RedirectResponse(url="/admin/users", status_code=302)


# ── Orders ────────────────────────────────────────────────────────────────────

@router.get("/orders", response_class=HTMLResponse)
async def orders_list(request: Request, db: AsyncSession = Depends(get_db), page: int = 1):
    admin = await _get_admin_user(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    per_page = 50
    offset   = (page - 1) * per_page
    result   = await db.execute(
        select(Order).order_by(Order.created_at.desc()).offset(offset).limit(per_page)
    )
    orders = result.scalars().all()
    total  = (await db.execute(select(func.count(Order.id)))).scalar_one()

    return templates.TemplateResponse(
        "orders.html",
        {"request": request, "admin": admin, "orders": orders,
         "page": page, "total": total, "per_page": per_page},
    )


@router.post("/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    new_status: str = Form(...),
):
    admin = await _get_admin_user(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order:
        try:
            target_status = OrderStatus(new_status)
        except ValueError:
            return RedirectResponse(url="/admin/orders", status_code=302)

        already_completed = order.status == OrderStatus.COMPLETED

        # Changing a BUY order to COMPLETED → credit gold to the user
        if (
            target_status == OrderStatus.COMPLETED
            and order.order_type == OrderType.BUY
            and not already_completed
        ):
            from app.services.order_service import complete_buy_order
            await complete_buy_order(db, order)
            await db.commit()

            user_result = await db.execute(select(User).where(User.id == order.user_id))
            user = user_result.scalar_one_or_none()
            if user:
                from app.services.notification_service import notify_user
                from app.bot.utils.formatting import grams as fmt_grams, usd
                try:
                    await notify_user(
                        user.telegram_id,
                        f"✅  <b>Payment Verified!</b>\n\n"
                        f"<b>{fmt_grams(order.grams)}</b> of gold has been credited to your vault.\n"
                        f"<b>Order:</b> <code>#{order_id}</code>  ·  {usd(order.total_usd)}\n\n"
                        f"<i>Your gold appreciates with the live market price.</i>"
                    )
                except Exception:
                    pass
        else:
            order.status = target_status
            await db.commit()

    return RedirectResponse(url="/admin/orders", status_code=302)


@router.post("/orders/{order_id}/approve_receipt")
async def approve_receipt(
    order_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Approve a submitted payment receipt → credit gold to user."""
    admin = await _get_admin_user(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    result = await db.execute(select(Order).where(Order.id == order_id))
    order  = result.scalar_one_or_none()

    if order and order.status == OrderStatus.PAID:
        from app.services.order_service import complete_buy_order
        await complete_buy_order(db, order)
        await db.commit()

        # Notify user
        user_result = await db.execute(select(User).where(User.id == order.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            from app.services.notification_service import notify_user
            from app.bot.utils.formatting import grams, usd
            try:
                await notify_user(
                    user.telegram_id,
                    f"✅  <b>Payment Verified!</b>\n\n"
                    f"<b>{grams(order.grams)}</b> of gold has been credited to your vault.\n"
                    f"<b>Order:</b> <code>#{order_id}</code>  ·  {usd(order.total_usd)}\n\n"
                    f"<i>Your gold appreciates with the live market price.</i>"
                )
            except Exception:
                pass

    return RedirectResponse(url="/admin/dashboard", status_code=302)


@router.post("/orders/{order_id}/reject_receipt")
async def reject_receipt(
    order_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_notes: str = Form(""),
):
    """Reject a submitted receipt → set order to FAILED."""
    admin = await _get_admin_user(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    result = await db.execute(select(Order).where(Order.id == order_id))
    order  = result.scalar_one_or_none()

    if order and order.status == OrderStatus.PAID:
        order.status      = OrderStatus.FAILED
        order.admin_notes = f"REJECTED: {admin_notes}"
        await db.commit()

        user_result = await db.execute(select(User).where(User.id == order.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            from app.services.notification_service import notify_user
            try:
                await notify_user(
                    user.telegram_id,
                    f"❌  <b>Receipt Rejected</b>\n\n"
                    f"Order <code>#{order_id}</code> could not be verified.\n"
                    f"<i>Reason: {admin_notes or 'Payment not confirmed'}</i>\n\n"
                    f"Please contact /support if you believe this is an error."
                )
            except Exception:
                pass

    return RedirectResponse(url="/admin/dashboard", status_code=302)


# ── Withdrawals ───────────────────────────────────────────────────────────────

@router.get("/withdrawals", response_class=HTMLResponse)
async def withdrawals_list(request: Request, db: AsyncSession = Depends(get_db)):
    admin = await _get_admin_user(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Withdrawal)
        .options(selectinload(Withdrawal.user))
        .order_by(Withdrawal.created_at.desc())
        .limit(200)
    )
    withdrawals = result.scalars().all()
    return templates.TemplateResponse(
        "withdrawals.html",
        {"request": request, "admin": admin, "withdrawals": withdrawals},
    )


@router.post("/withdrawals/{withdrawal_id}/approve")
async def approve_withdrawal(
    withdrawal_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_notes: str = Form(""),
):
    admin = await _get_admin_user(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    from app.services.withdrawal_service import approve_withdrawal as _approve
    await _approve(db, withdrawal_id, admin_notes or None)
    await db.commit()
    return RedirectResponse(url="/admin/withdrawals", status_code=302)


@router.post("/withdrawals/{withdrawal_id}/reject")
async def reject_withdrawal(
    withdrawal_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_notes: str = Form(""),
):
    admin = await _get_admin_user(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    from app.services.withdrawal_service import reject_withdrawal as _reject
    withdrawal = await _reject(db, withdrawal_id, admin_notes or None)
    await db.commit()

    if withdrawal:
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(Withdrawal).options(selectinload(Withdrawal.user)).where(Withdrawal.id == withdrawal_id)
        )
        w = result.scalar_one_or_none()
        if w and w.user:
            from app.services.notification_service import notify_user
            try:
                await notify_user(
                    w.user.telegram_id,
                    f"❌  <b>Withdrawal Rejected</b>\n\n"
                    f"Your withdrawal of <b>{w.gold_grams:.4f}g</b> gold was not approved.\n"
                    f"<i>Reason: {admin_notes or 'Not specified'}</i>\n\n"
                    f"Your gold has been refunded to your vault."
                )
            except Exception:
                pass

    return RedirectResponse(url="/admin/withdrawals", status_code=302)


@router.post("/withdrawals/{withdrawal_id}/complete")
async def complete_withdrawal(
    withdrawal_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tx_hash: str = Form(""),
):
    """Mark a withdrawal as completed after sending the crypto to user."""
    admin = await _get_admin_user(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    from app.services.withdrawal_service import complete_withdrawal as _complete
    withdrawal = await _complete(db, withdrawal_id, tx_hash or "manual")
    await db.commit()

    if withdrawal:
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(Withdrawal).options(selectinload(Withdrawal.user)).where(Withdrawal.id == withdrawal_id)
        )
        w = result.scalar_one_or_none()
        if w and w.user:
            from app.services.notification_service import notify_user
            try:
                await notify_user(
                    w.user.telegram_id,
                    f"✅  <b>Withdrawal Completed!</b>\n\n"
                    f"<b>{w.gold_grams:.4f}g</b> gold → <b>{w.crypto_type}</b> sent.\n"
                    f"💰  Amount: <b>${w.amount_usd:,.2f}</b>\n"
                    f"📬  Wallet: <code>{w.wallet_address}</code>\n"
                    + (f"🔗  TX: <code>{tx_hash}</code>" if tx_hash and tx_hash != "manual" else "")
                )
            except Exception:
                pass

    return RedirectResponse(url="/admin/withdrawals", status_code=302)


# ── Settings ──────────────────────────────────────────────────────────────────

async def _settings_context(request, admin, db, **extra) -> dict:
    """Build the full template context for the settings page."""
    # Trading
    markup    = await _get_setting("markup_percent",         settings.MARKUP_PERCENT)
    spread    = await _get_setting("spread_percent",         settings.SPREAD_PERCENT)
    min_buy   = await _get_setting("min_buy_grams",          settings.MIN_BUY_GRAMS)
    min_sell  = await _get_setting("min_sell_grams",         settings.MIN_SELL_GRAMS)
    referral  = await _get_setting("referral_bonus_percent", settings.REFERRAL_BONUS_PERCENT)
    price_lock = int(await _get_setting("PRICE_LOCK_DURATION", settings.PRICE_LOCK_DURATION))
    price_ttl  = int(await _get_setting("PRICE_CACHE_TTL",    settings.PRICE_CACHE_TTL))
    welcome_photo = await redis_get("admin:cfg:welcome_photo_url") or ""

    # NOWPayments
    np_api_key    = await _get_str("NOWPAYMENTS_API_KEY",      settings.NOWPAYMENTS_API_KEY)
    np_ipn_secret = await _get_str("NOWPAYMENTS_IPN_SECRET",   settings.NOWPAYMENTS_IPN_SECRET)
    np_callback   = await _get_str("NOWPAYMENTS_CALLBACK_URL", settings.NOWPAYMENTS_CALLBACK_URL)
    # Auto-suggest callback URL from request host
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host   = request.headers.get("x-forwarded-host", request.url.netloc)
    suggested_callback = f"{scheme}://{host}/api/v1/webhooks/nowpayments"

    # Price APIs
    gold_api_key  = await _get_str("GOLD_API_KEY",           settings.GOLD_API_KEY)
    exc_rate_key  = await _get_str("EXCHANGE_RATE_API_KEY",  settings.EXCHANGE_RATE_API_KEY)

    # Notifications & access
    admin_tg_ids      = await _get_str("ADMIN_TELEGRAM_IDS", settings.ADMIN_TELEGRAM_IDS)
    supported_cryptos = await _get_str("SUPPORTED_CRYPTOS",  settings.SUPPORTED_CRYPTOS)

    return {
        "request": request,
        "admin": admin,
        # Trading
        "markup": markup,
        "spread": spread,
        "min_buy": min_buy,
        "min_sell": min_sell,
        "referral": referral,
        "price_lock": price_lock,
        "price_ttl": price_ttl,
        "welcome_photo": welcome_photo,
        # NOWPayments
        "np_api_key": np_api_key,
        "np_ipn_secret": np_ipn_secret,
        "np_callback": np_callback,
        "suggested_callback": suggested_callback,
        # Price APIs
        "gold_api_key": gold_api_key,
        "exc_rate_key": exc_rate_key,
        # Notifications
        "admin_tg_ids": admin_tg_ids,
        "supported_cryptos": supported_cryptos,
        "saved": False,
        **extra,
    }


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: AsyncSession = Depends(get_db)):
    admin = await _get_admin_user(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)
    ctx = await _settings_context(request, admin, db)
    return templates.TemplateResponse("settings.html", ctx)


@router.post("/settings")
async def save_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    markup_percent: float = Form(...),
    spread_percent: float = Form(...),
    min_buy_grams: float = Form(...),
    min_sell_grams: float = Form(0.1),
    referral_bonus_percent: float = Form(...),
    price_lock_duration: int = Form(300),
    price_cache_ttl: int = Form(60),
    welcome_photo_url: str = Form(""),
    welcome_photo_file: Optional[UploadFile] = File(None),
):
    admin = await _get_admin_user(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    await _save_setting("markup_percent",         max(0.0, min(markup_percent, 20.0)))
    await _save_setting("spread_percent",         max(0.0, min(spread_percent, 20.0)))
    await _save_setting("min_buy_grams",          max(0.01, min_buy_grams))
    await _save_setting("min_sell_grams",         max(0.01, min_sell_grams))
    await _save_setting("referral_bonus_percent", max(0.0, min(referral_bonus_percent, 10.0)))
    await _save_setting("PRICE_LOCK_DURATION",    max(60, price_lock_duration))
    await _save_setting("PRICE_CACHE_TTL",        max(10, price_cache_ttl))

    from app.db.redis import redis_delete
    from app.services.notification_service import upload_photo_bytes
    import base64

    if welcome_photo_file and welcome_photo_file.filename:
        photo_bytes = await welcome_photo_file.read()
        if photo_bytes:
            # Always store as base64 so it works without any admin Telegram ID
            await redis_set("admin:cfg:welcome_photo_bytes", base64.b64encode(photo_bytes).decode())
            await redis_set("admin:cfg:welcome_photo_url", "__file__")
            await redis_delete("gold:photo:file_id:welcome")

            # Optional upgrade: if admin Telegram ID is available, upload to get
            # a stable Telegram file_id (faster delivery, no re-encoding needed)
            admin_ids_str = await redis_get("admin:cfg:ADMIN_TELEGRAM_IDS") or settings.ADMIN_TELEGRAM_IDS
            admin_ids = [int(x.strip()) for x in (admin_ids_str or "").split(",") if x.strip().isdigit()]
            if admin_ids:
                file_id = await upload_photo_bytes(photo_bytes, welcome_photo_file.filename, admin_ids[0])
                if file_id:
                    await redis_set("admin:cfg:welcome_photo_url", file_id)
    elif welcome_photo_url.strip():
        await redis_set("admin:cfg:welcome_photo_url", welcome_photo_url.strip())
        await redis_delete("gold:photo:file_id:welcome")
    # else: neither file nor URL provided — leave existing value untouched

    ctx = await _settings_context(request, admin, db, saved=True)
    return templates.TemplateResponse("settings.html", ctx)


# ── Settings: NOWPayments ─────────────────────────────────────────────────────

@router.post("/settings/payment")
async def save_payment_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    np_api_key: str = Form(""),
    np_ipn_secret: str = Form(""),
    np_callback: str = Form(""),
):
    admin = await _get_admin_user(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    if np_api_key.strip():
        await _save_str("NOWPAYMENTS_API_KEY", np_api_key)
    if np_ipn_secret.strip():
        await _save_str("NOWPAYMENTS_IPN_SECRET", np_ipn_secret)
    if np_callback.strip():
        await _save_str("NOWPAYMENTS_CALLBACK_URL", np_callback)

    ctx = await _settings_context(request, admin, db, saved="payment")
    return templates.TemplateResponse("settings.html", ctx)


# ── Settings: Price APIs ──────────────────────────────────────────────────────

@router.post("/settings/apis")
async def save_api_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    gold_api_key: str = Form(""),
    exc_rate_key: str = Form(""),
):
    admin = await _get_admin_user(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    if gold_api_key.strip():
        await _save_str("GOLD_API_KEY", gold_api_key)
        # Clear price cache so next fetch uses new key
        from app.db.redis import redis_delete
        await redis_delete("gold:price:current")
    if exc_rate_key.strip():
        await _save_str("EXCHANGE_RATE_API_KEY", exc_rate_key)

    ctx = await _settings_context(request, admin, db, saved="apis")
    return templates.TemplateResponse("settings.html", ctx)


# ── Settings: Notifications & System ─────────────────────────────────────────

@router.post("/settings/system")
async def save_system_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_tg_ids: str = Form(""),
    supported_cryptos: str = Form(""),
    new_password: str = Form(""),
    confirm_password: str = Form(""),
):
    admin = await _get_admin_user(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    error: Optional[str] = None

    if admin_tg_ids.strip():
        await _save_str("ADMIN_TELEGRAM_IDS", admin_tg_ids)
    if supported_cryptos.strip():
        await _save_str("SUPPORTED_CRYPTOS", supported_cryptos.upper())

    if new_password:
        if new_password != confirm_password:
            error = "Passwords do not match."
        elif len(new_password) < 8:
            error = "Password must be at least 8 characters."
        else:
            from app.admin.auth import hash_password
            admin.hashed_password = hash_password(new_password)
            await db.commit()

    ctx = await _settings_context(
        request, admin, db,
        saved="system" if not error else False,
        system_error=error,
    )
    return templates.TemplateResponse("settings.html", ctx)


# ── Broadcast ─────────────────────────────────────────────────────────────────

@router.post("/broadcast")
async def do_broadcast(
    request: Request,
    db: AsyncSession = Depends(get_db),
    broadcast_type: str = Form("text"),        # "text" | "photo" | "photo_text"
    message: Optional[str] = Form(None),
    photo_url: Optional[str] = Form(None),
    photo_file: Optional[UploadFile] = File(None),
):
    admin = await _get_admin_user(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    result = await db.execute(
        select(User.telegram_id).where(User.is_active == True, User.is_banned == False)  # noqa: E712
    )
    telegram_ids = [row[0] for row in result.all()]

    from app.services.notification_service import (
        broadcast_message as _broadcast_text,
        broadcast_photo_message as _broadcast_photo,
        upload_photo_bytes,
    )

    # Resolve photo: uploaded file → Telegram file_id → URL string
    resolved_photo: Optional[str] = photo_url.strip() if photo_url else None
    if broadcast_type in ("photo", "photo_text") and photo_file and photo_file.filename:
        photo_bytes = await photo_file.read()
        if photo_bytes:
            admin_ids = settings.admin_telegram_ids
            upload_target = admin_ids[0] if admin_ids else (telegram_ids[0] if telegram_ids else None)
            if upload_target:
                file_id = await upload_photo_bytes(photo_bytes, photo_file.filename, upload_target)
                if file_id:
                    resolved_photo = file_id

    stats: dict
    if broadcast_type == "text" and message:
        stats = await _broadcast_text(telegram_ids, message)
    elif broadcast_type in ("photo", "photo_text") and resolved_photo:
        caption = (message or "") if broadcast_type == "photo_text" else ""
        stats = await _broadcast_photo(telegram_ids, resolved_photo, caption)
    else:
        stats = {"success": 0, "failed": 0, "error": "No valid content to send. Add a message or photo."}

    ctx = await _settings_context(request, admin, db, broadcast_stats=stats)
    return templates.TemplateResponse("settings.html", ctx)
