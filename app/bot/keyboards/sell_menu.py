from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

SELL_CRYPTOS = [
    ("₿ BTC",    "BTC"),
    ("Ξ ETH",    "ETH"),
    ("💲 USDT",  "USDT"),
    ("◎ SOL",    "SOL"),
    ("✕ XRP",    "XRP"),
    ("Ł LTC",    "LTC"),
    ("⬡ BNB",    "BNB"),
    ("◈ MATIC",  "MATIC"),
    ("🔷 USDC",  "USDC"),
    ("Ð DOGE",   "DOGE"),
    ("⚡ TRX",   "TRX"),
    ("🔵 ADA",   "ADA"),
]


def sell_crypto_kb() -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(SELL_CRYPTOS), 3):
        chunk = SELL_CRYPTOS[i:i+3]
        rows.append([
            InlineKeyboardButton(text=label, callback_data=f"sell:crypto:{sym}")
            for label, sym in chunk
        ])
    rows.append([InlineKeyboardButton(text="🏠  Main Menu", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sell_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅  Confirm & Submit",  callback_data="sell:confirm")],
            [InlineKeyboardButton(text="✏️  Change Wallet",     callback_data="sell:change_wallet")],
            [InlineKeyboardButton(text="🏠  Main Menu",          callback_data="menu:main")],
        ]
    )
