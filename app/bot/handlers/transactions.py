from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main_menu import back_kb
from app.bot.utils.formatting import transactions_message
from app.bot.utils.helpers import gold_reply
from app.models.user import User
from app.services.order_service import get_user_orders
from app.services.withdrawal_service import get_user_withdrawals

router = Router(name="transactions")


@router.message(Command("transactions"))
@router.callback_query(F.data == "menu:transactions")
async def show_transactions(
    event: Message | CallbackQuery, user: User, db: AsyncSession
) -> None:
    orders      = await get_user_orders(db, user.id, limit=8)
    withdrawals = await get_user_withdrawals(db, user.id, limit=5)
    text        = transactions_message(orders, withdrawals)
    await gold_reply(event, text, back_kb(), context="transactions")
