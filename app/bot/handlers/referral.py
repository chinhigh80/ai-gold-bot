from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.utils.formatting import referral_message
from app.bot.utils.helpers import gold_reply
from app.config import settings
from app.models.user import User

router = Router(name="referral")

BOT_USERNAME = "AMIRAGOLDLUXURY_bot"


@router.message(Command("referral"))
@router.callback_query(F.data == "menu:referral")
async def show_referral(event: Message | CallbackQuery, user: User) -> None:
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user.referral_code}"

    text = referral_message(
        display_name=user.display_name,
        referral_code=user.referral_code,
        referral_link=referral_link,
        bonus_pct=settings.REFERRAL_BONUS_PERCENT,
        bonus_earned=user.referral_bonus_earned_usd,
    )

    share_url = (
        f"https://t.me/share/url"
        f"?url={referral_link}"
        f"&text=Join+AMIRA+GOLD+LUXURY+%E2%80%94+Buy+%26+sell+gold+at+live+UAE+prices"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤  Share My Referral Link", url=share_url)],
            [InlineKeyboardButton(text="🏠  Main Menu", callback_data="menu:main")],
        ]
    )
    await gold_reply(event, text, kb, context="referral")
