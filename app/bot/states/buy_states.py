from aiogram.fsm.state import State, StatesGroup


class BuyGold(StatesGroup):
    choosing_amount = State()
    custom_amount = State()
    choosing_crypto = State()
    confirming = State()
    uploading_receipt = State()
