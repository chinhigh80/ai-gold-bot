"""Start handler — luxury welcome with gold photo + live price."""
from __future__ import annotations

import structlog
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main_menu import main_menu_kb
from app.bot.utils.formatting import welcome_caption, welcome_message
from app.bot.utils.helpers import gold_reply
from app.models.user import User
from app.services.price_service import get_gold_price

logger = structlog.get_logger(__name__)
router = Router(name="start")


async def _fetch_price() -> float | None:
    try:
        pd = await get_gold_price()
        return pd.price_per_gram_usd
    except Exception:
        return None


# ── /start ─────────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, user: User, state: FSMContext) -> None:
    await state.clear()
    price   = await _fetch_price()
    caption = welcome_caption(
        display_name=user.display_name,
        price_per_gram=price,
        gold_grams=user.gold_grams,
    )
    await gold_reply(message, caption, main_menu_kb(), context="welcome")


# ── "Back to main menu" callback ───────────────────────────────────────────────

@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, user: User, state: FSMContext) -> None:
    await state.clear()
    price   = await _fetch_price()
    caption = welcome_caption(
        display_name=user.display_name,
        price_per_gram=price,
        gold_grams=user.gold_grams,
    )
    await gold_reply(callback, caption, main_menu_kb(), context="welcome")


# ── /help ──────────────────────────────────────────────────────────────────────

@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    from app.bot.utils.formatting import BRAND_HEADER, THICK_LINE, THIN_LINE

    text = (
        f"{BRAND_HEADER}  ·  <b>Commands</b>\n\n"
        f"{THICK_LINE}\n\n"
        f"🏠  /start        —  Main menu\n"
        f"💰  /buy          —  Buy gold\n"
        f"🔄  /sell         —  Sell gold\n"
        f"💳  /wallet       —  My vault & balance\n"
        f"📊  /transactions —  Order history\n"
        f"👥  /referral     —  Referral program\n"
        f"💬  /support      —  Help & FAQ\n\n"
        f"{THIN_LINE}\n\n"
        f"<i>For urgent issues use /support to reach our team.</i>"
    )
    await gold_reply(message, text, main_menu_kb(), context="default")
