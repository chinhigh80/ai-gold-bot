from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💰  Buy Gold",    callback_data="menu:buy"),
                InlineKeyboardButton(text="🔄  Sell Gold",   callback_data="menu:sell"),
            ],
            [
                InlineKeyboardButton(text="💳  My Vault",    callback_data="menu:wallet"),
                InlineKeyboardButton(text="📊  History",     callback_data="menu:transactions"),
            ],
            [
                InlineKeyboardButton(text="👥  Referral",    callback_data="menu:referral"),
                InlineKeyboardButton(text="💬  Support",     callback_data="menu:support"),
            ],
            [
                InlineKeyboardButton(text="💹  Live Price",  callback_data="menu:price"),
            ],
        ]
    )


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠  Main Menu", callback_data="menu:main")],
        ]
    )


def back_and_menu_kb(back_data: str, back_label: str = "«  Back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=back_label, callback_data=back_data)],
            [InlineKeyboardButton(text="🏠  Main Menu", callback_data="menu:main")],
        ]
    )
