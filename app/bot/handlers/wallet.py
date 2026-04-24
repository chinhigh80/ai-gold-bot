from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main_menu import back_kb
from app.bot.utils.formatting import wallet_message
from app.bot.utils.helpers import gold_reply
from app.models.user import User
from app.services.price_service import get_gold_price

router = Router(name="wallet")


@router.message(Command("wallet"))
@router.callback_query(F.data == "menu:wallet")
async def show_wallet(event: Message | CallbackQuery, user: User) -> None:
    try:
        pd = await get_gold_price()
        gold_value    = round(user.gold_grams * pd.price_per_gram_usd, 2)
        current_price = pd.price_per_gram_usd
    except Exception:
        gold_value    = 0.0
        current_price = 0.0

    text = wallet_message(
        display_name=user.display_name,
        gold_grams=user.gold_grams,
        gold_value_usd=gold_value,
        balance_usd=user.balance_usd,
        price_per_gram=current_price,
        referral_code=user.referral_code,
        bonus_earned=user.referral_bonus_earned_usd,
    )
    await gold_reply(event, text, back_kb(), context="wallet")
