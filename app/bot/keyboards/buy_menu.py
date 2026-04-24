from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# 12 preset amounts (grams)
PRESETS = [0.1, 0.5, 1, 2, 5, 10, 20, 50, 100, 250, 500, 1000]

# 22 supported cryptocurrencies
CRYPTOS = [
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
    ("🌐 DOT",   "DOT"),
    ("🔗 LINK",  "LINK"),
    ("🌀 AVAX",  "AVAX"),
    ("🔶 SHIB",  "SHIB"),
    ("💎 DAI",   "DAI"),
    ("⚙ ATOM",  "ATOM"),
    ("🌊 ALGO",  "ALGO"),
    ("🟣 XLM",   "XLM"),
    ("🔷 NEAR",  "NEAR"),
    ("🏔 XMR",   "XMR"),
]


def buy_amount_kb() -> InlineKeyboardMarkup:
    rows = []
    # 4 presets per row
    for i in range(0, len(PRESETS), 4):
        chunk = PRESETS[i:i+4]
        rows.append([
            InlineKeyboardButton(
                text=f"🥇 {g}g" if g >= 1 else f"🥇 {g}g",
                callback_data=f"buy:grams:{g}"
            )
            for g in chunk
        ])
    rows.append([InlineKeyboardButton(text="✏️  Custom Amount", callback_data="buy:custom")])
    rows.append([InlineKeyboardButton(text="🏠  Main Menu",     callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def buy_crypto_kb() -> InlineKeyboardMarkup:
    rows = []
    # 3 cryptos per row
    for i in range(0, len(CRYPTOS), 3):
        chunk = CRYPTOS[i:i+3]
        rows.append([
            InlineKeyboardButton(text=label, callback_data=f"buy:crypto:{sym}")
            for label, sym in chunk
        ])
    rows.append([InlineKeyboardButton(text="«  Back", callback_data="menu:buy")])
    rows.append([InlineKeyboardButton(text="🏠  Main Menu", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_kb(payment_url: str | None) -> InlineKeyboardMarkup:
    rows = []
    if payment_url:
        rows.append([InlineKeyboardButton(text="💳  Open Payment Page", url=payment_url)])
    rows.append([InlineKeyboardButton(text="🧾  Submit Payment Receipt", callback_data="buy:submit_receipt")])
    rows.append([InlineKeyboardButton(text="📊  My Orders",   callback_data="menu:transactions")])
    rows.append([InlineKeyboardButton(text="🏠  Main Menu",   callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def receipt_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌  Cancel", callback_data="buy:cancel_receipt")],
    ])
