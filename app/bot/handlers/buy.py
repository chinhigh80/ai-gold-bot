"""
Buy gold flow:
  1. menu:buy         → show preset amounts (photo)
  2. buy:grams:N      → price quote + choose crypto (photo)
  3. buy:custom       → type custom amount (FSM)
  4. buy:crypto:X     → create order + payment invoice (photo)
  5. buy:submit_receipt → FSM: user sends payment receipt screenshot/tx
  6. admin approves   → gold credited
"""
from __future__ import annotations

import structlog
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.buy_menu import (
    buy_amount_kb, buy_crypto_kb, payment_kb, receipt_cancel_kb,
)
from app.bot.keyboards.main_menu import back_and_menu_kb, back_kb
from app.bot.states.buy_states import BuyGold
from app.bot.utils.formatting import (
    BRAND_HEADER, THICK_LINE, THIN_LINE,
    buy_menu_message, buy_quote_message, payment_invoice_message,
)
from app.bot.utils.helpers import gold_reply, safe_edit
from app.config import settings
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.services.notification_service import notify_admins
from app.services.order_service import create_buy_order
from app.services.payment_service import create_payment
from app.services.price_service import calculate_buy_price, calculate_buy_price_async, get_gold_price

logger = structlog.get_logger(__name__)
router = Router(name="buy")


async def _price_or_none() -> tuple[float | None, float]:
    try:
        pd = await get_gold_price()
        result = await calculate_buy_price_async(pd.price_per_gram_usd, 1.0)
        return result["price_per_gram_usd"], result["markup_percent"]
    except Exception:
        return None, 2.5


# ── Entry ──────────────────────────────────────────────────────────────────────

@router.message(Command("buy"))
@router.callback_query(F.data == "menu:buy")
async def enter_buy(event: Message | CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BuyGold.choosing_amount)
    price, markup = await _price_or_none()
    text = buy_menu_message(price, markup)
    await gold_reply(event, text, buy_amount_kb(), context="buy")


# ── Preset amount ──────────────────────────────────────────────────────────────

@router.callback_query(BuyGold.choosing_amount, F.data.startswith("buy:grams:"))
async def cb_preset_amount(callback: CallbackQuery, state: FSMContext) -> None:
    grams = float(callback.data.split(":")[2])
    await _show_quote(callback, state, grams)


# ── Custom amount ──────────────────────────────────────────────────────────────

@router.callback_query(BuyGold.choosing_amount, F.data == "buy:custom")
async def cb_custom_amount(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BuyGold.custom_amount)
    text = (
        f"{BRAND_HEADER}  ·  <b>Custom Amount</b>\n\n"
        f"{THICK_LINE}\n\n"
        f"✏️  Enter the amount of gold in <b>grams</b>:\n\n"
        f"  <i>Min: <b>{settings.MIN_BUY_GRAMS} g</b>  ·  Any amount above</i>\n\n"
        f"<i>Examples: <code>0.5</code> · <code>2.5</code> · <code>250</code> · <code>1000</code></i>"
    )
    await safe_edit(callback.message, text, back_and_menu_kb("menu:buy"), context="buy")
    await callback.answer()


@router.message(BuyGold.custom_amount)
async def msg_custom_amount(message: Message, state: FSMContext) -> None:
    raw = message.text.strip().replace(",", ".")
    try:
        gram_amount = float(raw)
    except ValueError:
        await message.answer("❌ <b>Invalid input.</b>  Enter a number, e.g. <code>2.5</code>")
        return

    if gram_amount < settings.MIN_BUY_GRAMS:
        await message.answer(f"❌ Minimum is <b>{settings.MIN_BUY_GRAMS} g</b>.")
        return

    await state.update_data(grams=gram_amount)
    await state.set_state(BuyGold.choosing_crypto)

    try:
        pd = await get_gold_price()
        calc = calculate_buy_price(pd.price_per_gram_usd, gram_amount)
    except RuntimeError:
        await message.answer("⚠️ Price service temporarily unavailable. Please try again.")
        return

    text = buy_quote_message(
        gram_amount=gram_amount,
        base_price=calc["base_price_per_gram_usd"],
        marked_price=calc["price_per_gram_usd"],
        total=calc["total_usd"],
        markup=calc["markup_percent"],
        lock_minutes=settings.PRICE_LOCK_DURATION // 60,
    )
    await gold_reply(message, text, buy_crypto_kb(), context="buy")


# ── Show quote ─────────────────────────────────────────────────────────────────

async def _show_quote(callback: CallbackQuery, state: FSMContext, gram_amount: float) -> None:
    await state.update_data(grams=gram_amount)
    await state.set_state(BuyGold.choosing_crypto)

    try:
        pd = await get_gold_price()
        calc = calculate_buy_price(pd.price_per_gram_usd, gram_amount)
    except RuntimeError:
        await callback.answer("⚠️ Price service unavailable. Try again.", show_alert=True)
        return

    text = buy_quote_message(
        gram_amount=gram_amount,
        base_price=calc["base_price_per_gram_usd"],
        marked_price=calc["price_per_gram_usd"],
        total=calc["total_usd"],
        markup=calc["markup_percent"],
        lock_minutes=settings.PRICE_LOCK_DURATION // 60,
    )
    await safe_edit(callback.message, text, buy_crypto_kb(), context="buy")
    await callback.answer()


# ── Crypto chosen → create order & invoice ─────────────────────────────────────

@router.callback_query(BuyGold.choosing_crypto, F.data.startswith("buy:crypto:"))
async def cb_choose_crypto(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User,
) -> None:
    crypto       = callback.data.split(":")[2]
    data         = await state.get_data()
    gram_amount: float = data.get("grams", 1.0)

    await safe_edit(callback.message, f"{BRAND_HEADER}\n\n⏳  <b>Creating your order…</b>", context="buy")
    await callback.answer()

    try:
        order   = await create_buy_order(db, user, gram_amount, crypto)
        invoice = await create_payment(order.total_usd, crypto, order.id)

        order.payment_id      = invoice.payment_id
        order.payment_url     = invoice.payment_url
        order.payment_address = invoice.payment_address
        order.crypto_amount   = invoice.pay_amount
        order.status          = OrderStatus.AWAITING_PAYMENT
        await db.flush()
        await state.update_data(order_id=order.id)
        await state.set_state(BuyGold.confirming)

        text = payment_invoice_message(
            order_id=order.id,
            gram_amount=order.grams,
            total_usd=order.total_usd,
            crypto_amount=invoice.pay_amount,
            crypto_currency=crypto,
            pay_address=invoice.payment_address or "—",
        )
        await safe_edit(callback.message, text, payment_kb(invoice.payment_url), context="buy")

    except Exception as e:
        logger.error("buy_order_failed", error=str(e), user_id=user.id)
        await state.clear()
        await safe_edit(
            callback.message,
            f"{BRAND_HEADER}\n\n❌  <b>Could not create order.</b>\n\n"
            f"<i>{str(e)[:200]}</i>\n\nPlease try again or contact /support",
            back_kb(),
            context="buy",
        )


# ── Receipt submission ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "buy:submit_receipt")
async def cb_submit_receipt(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("order_id"):
        await callback.answer("❌ No active order found.", show_alert=True)
        return

    await state.set_state(BuyGold.uploading_receipt)
    text = (
        f"{BRAND_HEADER}  ·  <b>Submit Payment Receipt</b>\n\n"
        f"{THICK_LINE}\n\n"
        f"📸  Send your payment proof:\n\n"
        f"  • <b>Screenshot</b> of your payment confirmation, OR\n"
        f"  • Your <b>Transaction ID / TX Hash</b> as text\n\n"
        f"{THIN_LINE}\n\n"
        f"<i>Our team will verify and credit your gold within <b>30 minutes</b>.</i>"
    )
    await safe_edit(callback.message, text, receipt_cancel_kb(), context="buy")
    await callback.answer()


@router.callback_query(BuyGold.uploading_receipt, F.data == "buy:cancel_receipt")
async def cb_cancel_receipt(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(BuyGold.confirming)
    text = (
        f"{BRAND_HEADER}  ·  <b>Payment Invoice</b>\n\n"
        f"{THICK_LINE}\n\n"
        f"📋  <b>Order:</b>  <code>#{data.get('order_id', '?')}</code>\n\n"
        f"<i>Use the buttons below to submit your receipt or check your orders.</i>"
    )
    from app.bot.keyboards.buy_menu import payment_kb
    await safe_edit(callback.message, text, payment_kb(None), context="buy")
    await callback.answer()


@router.message(BuyGold.uploading_receipt)
async def msg_receipt_upload(message: Message, state: FSMContext, db: AsyncSession, user: User) -> None:
    from sqlalchemy import select
    data     = await state.get_data()
    order_id = data.get("order_id")

    if not order_id:
        await message.answer("❌ No active order. Please start a new buy order.")
        await state.clear()
        return

    # Accept photo or text (tx hash)
    receipt_ref: str | None = None
    if message.photo:
        receipt_ref = f"PHOTO:{message.photo[-1].file_id}"
    elif message.text and len(message.text.strip()) >= 8:
        receipt_ref = f"TEXT:{message.text.strip()}"
    else:
        await message.answer(
            "❌ Please send a <b>screenshot</b> of your payment or your <b>transaction ID</b>."
        )
        return

    # Save receipt to order admin_notes
    result = await db.execute(select(Order).where(Order.id == order_id))
    order  = result.scalar_one_or_none()
    if not order:
        await message.answer("❌ Order not found.")
        await state.clear()
        return

    order.admin_notes = f"RECEIPT:{receipt_ref}"
    order.status      = OrderStatus.PAID
    await db.flush()
    await state.clear()

    # Notify admins
    from app.bot.utils.formatting import grams, usd
    await notify_admins(
        f"🧾  <b>Payment Receipt Submitted</b>\n\n"
        f"👤  {user.display_name}  (ID: <code>{user.telegram_id}</code>)\n"
        f"📋  Order <code>#{order_id}</code>  ·  {grams(order.grams)}  ·  {usd(order.total_usd)}\n"
        f"🪙  {order.crypto_currency}\n\n"
        f"<b>Receipt:</b> {'[Photo attached]' if receipt_ref.startswith('PHOTO:') else receipt_ref[5:]}\n\n"
        f"👉  Approve at: http://localhost:8000/admin/orders"
    )

    # If receipt is a photo, forward it to admins
    if receipt_ref.startswith("PHOTO:") and settings.admin_telegram_ids:
        from app.bot.main import _bot_instance
        file_id = receipt_ref[6:]
        for admin_id in settings.admin_telegram_ids:
            try:
                if _bot_instance:
                    await _bot_instance.send_photo(admin_id, photo=file_id, caption=f"Receipt for order #{order_id}")
            except Exception:
                pass

    await gold_reply(
        message,
        (
            f"{BRAND_HEADER}  ·  <b>Receipt Received!</b>\n\n"
            f"{THICK_LINE}\n\n"
            f"✅  <b>Thank you!</b> Your receipt has been submitted.\n\n"
            f"📋  <b>Order:</b>  <code>#{order_id}</code>\n"
            f"⏳  <b>Status:</b>  Awaiting Admin Verification\n\n"
            f"{THIN_LINE}\n\n"
            f"<i>Gold will be credited to your vault within <b>30 minutes</b>\n"
            f"after payment is verified. You'll receive a notification.</i>"
        ),
        back_kb(),
        context="buy",
    )


# ── Live price quick-view ──────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:price")
async def cb_live_price(callback: CallbackQuery) -> None:
    from app.bot.utils.formatting import THIN_LINE, usd, pct
    from app.services.price_service import calculate_sell_price

    try:
        pd     = await get_gold_price()
        buy_p  = calculate_buy_price(pd.price_per_gram_usd, 1.0)["price_per_gram_usd"]
        sell_p = calculate_sell_price(pd.price_per_gram_usd, 1.0)["price_per_gram_usd"]
        text = (
            f"{BRAND_HEADER}  ·  <b>Live Gold Price</b>\n\n"
            f"{THICK_LINE}\n\n"
            f"📊  <b>Spot Price:</b>    <code>{usd(pd.price_per_gram_usd)}/g</code>\n\n"
            f"{THIN_LINE}\n\n"
            f"💰  <b>Buy Price:</b>     <code>{usd(buy_p)}/g</code>  "
            f"<i>(+{pct(settings.MARKUP_PERCENT)} spread)</i>\n"
            f"🔄  <b>Sell Price:</b>    <code>{usd(sell_p)}/g</code>  "
            f"<i>(-{pct(settings.SPREAD_PERCENT)} spread)</i>\n\n"
            f"{THIN_LINE}\n\n"
            f"🌍  <b>Source:</b>  XAU/USD · UAE Market\n"
            f"🕐  <b>Updated:</b> Every 60 seconds"
        )
    except Exception:
        text = f"{BRAND_HEADER}\n\n⚠️  Price service temporarily unavailable."

    from app.bot.keyboards.main_menu import back_kb
    await safe_edit(callback.message, text, back_kb(), context="buy")
    await callback.answer()
