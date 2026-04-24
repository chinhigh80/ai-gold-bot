from aiogram.fsm.state import State, StatesGroup


class SellGold(StatesGroup):
    entering_amount = State()
    choosing_crypto = State()
    entering_wallet = State()
    confirming = State()
