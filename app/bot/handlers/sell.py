"""
Sell gold flow:
  1. menu:sell       → show holdings + enter amount (FSM)
  2. user types grams → quote + choose crypto
  3. sell:crypto:X   → prompt for wallet address (FSM)
  4. user types wallet → confirmation screen
  5. sell:confirm    → create sell order + notify admins
"""
from __future__ import annotations

import structlog
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main_menu import back_and_menu_kb, back_kb
from app.bot.keyboards.sell_menu import sell_confirm_kb, sell_crypto_kb
from app.bot.states.sell_states import SellGold
from app.bot.utils.formatting import (
    BRAND_HEADER, THICK_LINE,
    sell_confirm_message, sell_menu_message, sell_quote_message,
    sell_submitted_message, sell_wallet_prompt,
)
from app.bot.utils.helpers import gold_reply, safe_edit
from app.config import settings
from app.models.user import User
from app.services.notification_service import notify_admins
from app.services.order_service import create_sell_order
from app.services.price_service import calculate_sell_price, calculate_sell_price_async, get_gold_price

logger = structlog.get_logger(__name__)
router = Router(name="sell")


# ── Entry ──────────────────────────────────────────────────────────────────────

@router.message(Command("sell"))
@router.callback_query(F.data == "menu:sell")
async def enter_sell(event: Message | CallbackQuery, user: User, state: FSMContext) -> None:
    await state.clear()

    # Guard: must have gold to sell
    if user.gold_grams < settings.MIN_SELL_GRAMS:
        text = (
            f"{BRAND_HEADER}  ·  <b>Sell Gold</b>\n\n"
            f"{THICK_LINE}\n\n"
            f"❌  <b>Insufficient Gold Balance</b>\n\n"
            f"You currently hold  <code>{user.gold_grams:.4f} g</code>\n"
            f"Minimum sell is  <code>{settings.MIN_SELL_GRAMS} g</code>\n\n"
            f"<i>Buy gold first to build your vault. 🥇</i>"
        )
        await gold_reply(event, text, back_kb(), context="sell")
        return

    sell_price = None
    spread = 1.5
    try:
        pd = await get_gold_price()
        result = await calculate_sell_price_async(pd.price_per_gram_usd, 1.0)
        sell_price = result["price_per_gram_usd"]
        spread = result["spread_percent"]
    except Exception:
        pass

    await state.set_state(SellGold.entering_amount)
    text = sell_menu_message(user.gold_grams, sell_price, spread)
    await gold_reply(event, text, back_kb(), context="sell")


# ── User types amount ──────────────────────────────────────────────────────────

@router.message(SellGold.entering_amount)
async def msg_sell_amount(message: Message, state: FSMContext, user: User) -> None:
    raw = message.text.strip().replace(",", ".")
    try:
        gram_amount = float(raw)
    except ValueError:
        await message.answer("❌ <b>Invalid input.</b>  Enter a number, e.g. <code>5.5</code>")
        return

    if gram_amount < settings.MIN_SELL_GRAMS:
        await message.answer(f"❌ Minimum sell is <b>{settings.MIN_SELL_GRAMS} g</b>.")
        return
    if gram_amount > user.gold_grams:
        from app.bot.utils.formatting import grams
        await message.answer(
            f"❌ <b>Insufficient balance.</b>\n\n"
            f"You hold  <code>{grams(user.gold_grams)}</code>.  "
            f"Please enter a lower amount."
        )
        return

    try:
        pd = await get_gold_price()
        calc = calculate_sell_price(pd.price_per_gram_usd, gram_amount)
    except RuntimeError:
        await message.answer("⚠️  Price service temporarily unavailable. Please try again.")
        return

    await state.update_data(grams=gram_amount, calc=calc)
    await state.set_state(SellGold.choosing_crypto)

    await gold_reply(
        message,
        sell_quote_message(
            gram_amount=gram_amount,
            base_price=calc["base_price_per_gram_usd"],
            net_price=calc["price_per_gram_usd"],
            total=calc["total_usd"],
            spread=calc["spread_percent"],
        ),
        sell_crypto_kb(),
        context="sell",
    )


# ── Crypto chosen ──────────────────────────────────────────────────────────────

@router.callback_query(SellGold.choosing_crypto, F.data.startswith("sell:crypto:"))
async def cb_sell_crypto(callback: CallbackQuery, state: FSMContext) -> None:
    crypto = callback.data.split(":")[2]
    await state.update_data(crypto=crypto)
    await state.set_state(SellGold.entering_wallet)
    await safe_edit(callback.message, sell_wallet_prompt(crypto), back_and_menu_kb("menu:sell"), context="sell")
    await callback.answer()


# ── User types wallet ──────────────────────────────────────────────────────────

@router.message(SellGold.entering_wallet)
async def msg_sell_wallet(message: Message, state: FSMContext) -> None:
    wallet = message.text.strip()
    if len(wallet) < 10:
        await message.answer("❌ <b>Invalid wallet address.</b>  Please try again.")
        return

    data = await state.get_data()
    calc        = data["calc"]
    gram_amount = data["grams"]
    crypto      = data["crypto"]

    await state.update_data(wallet=wallet)
    await state.set_state(SellGold.confirming)

    await gold_reply(
        message,
        sell_confirm_message(
            gram_amount=gram_amount,
            total_usd=calc["total_usd"],
            crypto=crypto,
            wallet=wallet,
            net_price=calc["price_per_gram_usd"],
        ),
        sell_confirm_kb(),
        context="sell",
    )


# ── Change wallet ──────────────────────────────────────────────────────────────

@router.callback_query(SellGold.confirming, F.data == "sell:change_wallet")
async def cb_change_wallet(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(SellGold.entering_wallet)
    await safe_edit(
        callback.message,
        sell_wallet_prompt(data.get("crypto", "crypto")),
        back_and_menu_kb("menu:sell"),
        context="sell",
    )
    await callback.answer()


# ── Confirm → create order ─────────────────────────────────────────────────────

@router.callback_query(SellGold.confirming, F.data == "sell:confirm")
async def cb_confirm_sell(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User,
) -> None:
    data        = await state.get_data()
    gram_amount = data["grams"]
    crypto      = data["crypto"]
    wallet      = data["wallet"]

    await safe_edit(callback.message, f"{BRAND_HEADER}\n\n⏳  <b>Submitting your sell order…</b>")
    await callback.answer()

    try:
        order = await create_sell_order(db, user, gram_amount, crypto, wallet)
        await state.clear()

        await safe_edit(
            callback.message,
            sell_submitted_message(order.id, gram_amount, order.total_usd, crypto),
            back_kb(),
        )

        from app.bot.utils.formatting import usd, grams
        await notify_admins(
            f"🔔  <b>New Sell Order</b>  #{order.id}\n\n"
            f"👤  {user.display_name}  (ID: <code>{user.telegram_id}</code>)\n"
            f"🔄  {grams(gram_amount)}  →  {usd(order.total_usd)}\n"
            f"🪙  Payout: <b>{crypto}</b>\n"
            f"📬  <code>{wallet[:30]}…</code>"
        )

    except (ValueError, Exception) as e:
        logger.error("sell_order_failed", error=str(e), user_id=user.id)
        await state.clear()
        await safe_edit(
            callback.message,
            f"{BRAND_HEADER}\n\n"
            f"❌  <b>Order failed.</b>\n\n"
            f"<i>{str(e)[:200]}</i>\n\n"
            f"Please try again or contact /support",
            back_kb(),
        )
