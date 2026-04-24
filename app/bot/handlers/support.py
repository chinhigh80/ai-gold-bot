from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.keyboards.main_menu import back_kb
from app.bot.utils.formatting import faq_message, support_message
from app.bot.utils.helpers import gold_reply, safe_edit
from app.db.redis import redis_get

router = Router(name="support")


async def _support_kb() -> InlineKeyboardMarkup:
    username = await redis_get("admin:cfg:SUPPORT_USERNAME") or "goldvault_support"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📨  Contact Support", url=f"https://t.me/{username}")],
            [InlineKeyboardButton(text="❓  View FAQ",        callback_data="support:faq")],
            [InlineKeyboardButton(text="🏠  Main Menu",       callback_data="menu:main")],
        ]
    )


@router.message(Command("support"))
@router.callback_query(F.data == "menu:support")
async def show_support(event: Message | CallbackQuery) -> None:
    await gold_reply(event, support_message(), await _support_kb(), context="support")


@router.callback_query(F.data == "support:faq")
async def show_faq(callback: CallbackQuery) -> None:
    await safe_edit(callback.message, faq_message(), back_kb())
    await callback.answer()
