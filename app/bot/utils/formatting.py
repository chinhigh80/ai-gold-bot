"""
Luxury HTML formatting for @AMIRAGOLDLUXURY_bot.

All messages use Telegram HTML parse mode.  No Markdown — HTML gives us full
control over bold, italic, code and links without escaping surprises.
"""
from __future__ import annotations

from datetime import datetime, timezone

# ── Brand constants ────────────────────────────────────────────────────────────

BRAND_NAME   = "AMIRA GOLD LUXURY"
BRAND_HEADER = "✨ <b>AMIRA GOLD LUXURY</b>"
THIN_LINE    = "─" * 30
THICK_LINE   = "═" * 30

# Status badges
BADGE = {
    "completed":        "✅",
    "pending":          "🕐",
    "awaiting_payment": "💳",
    "price_locked":     "🔒",
    "processing":       "⚙️",
    "cancelled":        "❌",
    "failed":           "❌",
    "expired":          "⌛",
    "approved":         "✔️",
    "rejected":         "✖️",
}


# ── Number formatters ──────────────────────────────────────────────────────────

def usd(amount: float) -> str:
    return f"${amount:,.2f}"


def grams(amount: float) -> str:
    if amount >= 1000:
        return f"{amount / 1000:.4f} kg"
    return f"{amount:.4f} g"


def pct(value: float) -> str:
    return f"{value:.2f}%"


# ── Welcome / Start ────────────────────────────────────────────────────────────

def welcome_caption(
    display_name: str,
    price_per_gram: float | None = None,
    gold_grams: float = 0.0,
) -> str:
    """Compact caption for the welcome photo (≤1024 chars for Telegram)."""
    price_line = (
        f"\n💹  <b>Gold Price:</b>  <code>{usd(price_per_gram)}/g</code>"
        if price_per_gram else ""
    )
    holdings_line = (
        f"\n🥇  <b>Your Vault:</b>  <code>{grams(gold_grams)}</code>"
        if gold_grams > 0 else ""
    )
    return (
        f"✨ <b>AMIRA GOLD LUXURY</b>\n"
        f"<i>Premium Gold Trading · UAE Market</i>\n\n"
        f"👑  Welcome, <b>{display_name}</b>!{price_line}{holdings_line}\n\n"
        f"{'═' * 24}\n\n"
        f"💰  Buy & sell gold at <b>live UAE prices</b>\n"
        f"⚡  Instant crypto payouts — <b>BTC · ETH · USDT</b>\n"
        f"🔒  Your vault is <b>fully secured & audited</b>\n"
        f"🌍  Available <b>24/7</b>, anywhere in the world\n\n"
        f"<i>Select an option below to begin:</i>"
    )


def welcome_message(
    display_name: str,
    price_per_gram: float | None = None,
    gold_grams: float = 0.0,
) -> str:
    """Full-length welcome for text-mode (after photo is dismissed)."""
    price_line = (
        f"\n💹  <b>Live Gold Price:</b>  <code>{usd(price_per_gram)}/g</code>"
        if price_per_gram else ""
    )
    holdings_line = (
        f"\n🥇  <b>Your Holdings:</b>  <code>{grams(gold_grams)}</code>"
        if gold_grams > 0 else ""
    )
    return (
        f"{BRAND_HEADER}\n"
        f"<i>Premium Gold Trading · UAE Market</i>\n\n"
        f"{THICK_LINE}\n\n"
        f"👑  Welcome back, <b>{display_name}</b>!\n"
        f"{price_line}"
        f"{holdings_line}\n\n"
        f"{THIN_LINE}\n\n"
        f"💰  Buy & sell gold at <b>real-time UAE prices</b>\n"
        f"⚡  <b>Instant</b> crypto payments — BTC · ETH · USDT\n"
        f"🔒  Your vault is <b>fully secured</b> & audited\n"
        f"🌍  Available <b>24 / 7</b>, anywhere in the world\n\n"
        f"{THIN_LINE}\n\n"
        f"<i>Select an option below to begin:</i>"
    )


# ── Buy flow ───────────────────────────────────────────────────────────────────

def buy_menu_message(price_per_gram: float | None, markup: float = 2.5) -> str:
    price_line = (
        f"\n💹  <b>Live Price:</b>  <code>{usd(price_per_gram)}/g</code>  "
        f"<i>(incl. {pct(markup)} buy spread)</i>"
        if price_per_gram
        else ""
    )
    return (
        f"{BRAND_HEADER}  ·  <b>Buy Gold</b>\n\n"
        f"{THIN_LINE}"
        f"{price_line}\n\n"
        f"Choose a <b>preset weight</b> or enter a custom amount:\n\n"
        f"  🥇  <b>1 g</b>   ·   <b>5 g</b>   ·   <b>10 g</b>\n"
        f"  🏅  <b>50 g</b>  ·   <b>100 g</b>  ·   Custom\n\n"
        f"{THIN_LINE}"
    )


def buy_quote_message(
    gram_amount: float,
    base_price: float,
    marked_price: float,
    total: float,
    markup: float,
    lock_minutes: int = 5,
) -> str:
    return (
        f"{BRAND_HEADER}  ·  <b>Price Quote</b>\n\n"
        f"{THICK_LINE}\n\n"
        f"🥇  <b>Amount:</b>         <code>{grams(gram_amount)}</code>\n"
        f"📊  <b>Spot price:</b>    <code>{usd(base_price)}/g</code>\n"
        f"📈  <b>Buy price:</b>     <code>{usd(marked_price)}/g</code>  "
        f"<i>(+{pct(markup)} spread)</i>\n\n"
        f"{THIN_LINE}\n\n"
        f"💵  <b>Total payable:</b>\n"
        f"    <code>{usd(total)}</code>\n\n"
        f"{THIN_LINE}\n\n"
        f"⏱  <i>Price locked for <b>{lock_minutes} minutes</b>.</i>\n"
        f"🪙  <i>Choose your payment cryptocurrency:</i>"
    )


def payment_invoice_message(
    order_id: int,
    gram_amount: float,
    total_usd: float,
    crypto_amount: float,
    crypto_currency: str,
    pay_address: str,
) -> str:
    return (
        f"{BRAND_HEADER}  ·  <b>Payment Invoice</b>\n\n"
        f"{THICK_LINE}\n\n"
        f"📋  <b>Order:</b>   <code>#{order_id}</code>\n"
        f"🥇  <b>Gold:</b>    <code>{grams(gram_amount)}</code>\n"
        f"💵  <b>Value:</b>   <code>{usd(total_usd)}</code>\n\n"
        f"{THIN_LINE}\n\n"
        f"<b>Send exactly:</b>\n"
        f"<code>{crypto_amount:.8f} {crypto_currency}</code>\n\n"
        f"<b>To this address:</b>\n"
        f"<code>{pay_address}</code>\n\n"
        f"{THIN_LINE}\n\n"
        f"⚠️  Send the <b>exact amount</b> shown above.\n"
        f"🔔  You will be notified once payment is confirmed.\n"
        f"⌛  <i>Invoice expires in 60 minutes.</i>"
    )


# ── Sell flow ──────────────────────────────────────────────────────────────────

def sell_menu_message(holding_grams: float, price_per_gram: float | None, spread: float = 1.5) -> str:
    price_line = (
        f"\n💹  <b>Sell Price:</b>  <code>{usd(price_per_gram)}/g</code>  "
        f"<i>(after {pct(spread)} spread)</i>"
        if price_per_gram
        else ""
    )
    return (
        f"{BRAND_HEADER}  ·  <b>Sell Gold</b>\n\n"
        f"{THIN_LINE}\n\n"
        f"🥇  <b>Your Holdings:</b>  <code>{grams(holding_grams)}</code>"
        f"{price_line}\n\n"
        f"{THIN_LINE}\n\n"
        f"Enter the amount of gold (in grams) you want to sell:\n\n"
        f"  <i>Minimum: <b>0.1 g</b>   ·   Maximum: your full balance</i>"
    )


def sell_quote_message(
    gram_amount: float,
    base_price: float,
    net_price: float,
    total: float,
    spread: float,
) -> str:
    return (
        f"{BRAND_HEADER}  ·  <b>Sell Quote</b>\n\n"
        f"{THICK_LINE}\n\n"
        f"🔄  <b>Selling:</b>         <code>{grams(gram_amount)}</code>\n"
        f"📊  <b>Spot price:</b>     <code>{usd(base_price)}/g</code>\n"
        f"📉  <b>Sell price:</b>     <code>{usd(net_price)}/g</code>  "
        f"<i>(-{pct(spread)} spread)</i>\n\n"
        f"{THIN_LINE}\n\n"
        f"💸  <b>You will receive:</b>\n"
        f"    <code>{usd(total)}</code>\n\n"
        f"{THIN_LINE}\n\n"
        f"<i>Choose your <b>payout cryptocurrency</b>:</i>"
    )


def sell_wallet_prompt(crypto: str) -> str:
    return (
        f"{BRAND_HEADER}  ·  <b>Sell Gold</b>\n\n"
        f"{THIN_LINE}\n\n"
        f"📬  Enter your <b>{crypto}</b> wallet address:\n\n"
        f"<i>Double-check carefully — crypto payouts are irreversible.</i>"
    )


def sell_confirm_message(
    gram_amount: float,
    total_usd: float,
    crypto: str,
    wallet: str,
    net_price: float,
) -> str:
    return (
        f"{BRAND_HEADER}  ·  <b>Confirm Sell Order</b>\n\n"
        f"{THICK_LINE}\n\n"
        f"🔄  <b>Selling:</b>       <code>{grams(gram_amount)}</code>\n"
        f"💸  <b>You receive:</b>   <code>{usd(total_usd)}</code>\n"
        f"🪙  <b>Payout in:</b>     <code>{crypto}</code>\n"
        f"📊  <b>Rate:</b>          <code>{usd(net_price)}/g</code>\n\n"
        f"{THIN_LINE}\n\n"
        f"📬  <b>Destination wallet:</b>\n"
        f"<code>{wallet}</code>\n\n"
        f"{THIN_LINE}\n\n"
        f"⚠️  <b>Please verify your wallet address.</b>\n"
        f"<i>Crypto payouts cannot be reversed once sent.</i>"
    )


def sell_submitted_message(order_id: int, gram_amount: float, total_usd: float, crypto: str) -> str:
    return (
        f"{BRAND_HEADER}  ·  <b>Sell Order Submitted</b>\n\n"
        f"{THICK_LINE}\n\n"
        f"✅  <b>Order <code>#{order_id}</code> received!</b>\n\n"
        f"🔄  <b>Selling:</b>     <code>{grams(gram_amount)}</code>\n"
        f"💸  <b>Payout:</b>      <code>{usd(total_usd)}</code> in <b>{crypto}</b>\n\n"
        f"{THIN_LINE}\n\n"
        f"🕐  <b>Status:</b>  Pending Admin Approval\n\n"
        f"<i>Our team processes withdrawals within <b>24 hours</b>.\n"
        f"You will receive a Telegram notification when your\n"
        f"crypto has been sent.</i>"
    )


# ── Wallet ─────────────────────────────────────────────────────────────────────

def wallet_message(
    display_name: str,
    gold_grams: float,
    gold_value_usd: float,
    balance_usd: float,
    price_per_gram: float,
    referral_code: str,
    bonus_earned: float,
) -> str:
    total_net_worth = gold_value_usd + balance_usd
    return (
        f"{BRAND_HEADER}  ·  <b>My Vault</b>\n\n"
        f"{THICK_LINE}\n\n"
        f"👤  <b>{display_name}</b>\n\n"
        f"{THIN_LINE}\n\n"
        f"🥇  <b>Gold Holdings</b>\n"
        f"    <code>{grams(gold_grams)}</code>  ≈  <code>{usd(gold_value_usd)}</code>\n\n"
        f"💵  <b>USD Balance</b>\n"
        f"    <code>{usd(balance_usd)}</code>\n\n"
        f"📈  <b>Net Worth</b>\n"
        f"    <code>{usd(total_net_worth)}</code>\n\n"
        f"{THIN_LINE}\n\n"
        f"💹  <b>Live Gold Price:</b>   <code>{usd(price_per_gram)}/g</code>\n\n"
        f"{THIN_LINE}\n\n"
        f"🔗  <b>Referral Code:</b>  <code>{referral_code}</code>\n"
        f"🎁  <b>Bonus Earned:</b>   <code>{usd(bonus_earned)}</code>"
    )


# ── Transactions ───────────────────────────────────────────────────────────────

def transactions_message(orders: list, withdrawals: list) -> str:
    lines = [
        f"{BRAND_HEADER}  ·  <b>History</b>\n\n{THICK_LINE}",
    ]

    if orders:
        lines.append("\n<b>📋  Recent Orders</b>")
        lines.append(THIN_LINE)
        for o in orders:
            badge = BADGE.get(o.status.value, "🔵")
            typ = "💰 BUY" if o.order_type.value == "buy" else "🔄 SELL"
            lines.append(
                f"{badge}  <b>#{o.id}</b>  ·  {typ}\n"
                f"      {grams(o.grams)}  ·  <code>{usd(o.total_usd)}</code>\n"
                f"      <i>{o.status.value.replace('_', ' ').title()}</i>"
            )
    else:
        lines.append(
            f"\n<i>No orders yet.\nTap <b>Buy Gold</b> to make your first trade! 🥇</i>"
        )

    if withdrawals:
        lines.append(f"\n<b>💸  Recent Withdrawals</b>")
        lines.append(THIN_LINE)
        for w in withdrawals:
            badge = BADGE.get(w.status.value, "🔵")
            lines.append(
                f"{badge}  <b>#{w.id}</b>  ·  {grams(w.gold_grams)}\n"
                f"      → <code>{usd(w.amount_usd)}</code> in <b>{w.crypto_type}</b>\n"
                f"      <i>{w.status.value.title()}</i>"
            )

    lines.append(f"\n{THICK_LINE}")
    return "\n".join(lines)


# ── Referral ───────────────────────────────────────────────────────────────────

def referral_message(
    display_name: str,
    referral_code: str,
    referral_link: str,
    bonus_pct: float,
    bonus_earned: float,
) -> str:
    return (
        f"{BRAND_HEADER}  ·  <b>Referral Program</b>\n\n"
        f"{THICK_LINE}\n\n"
        f"👤  <b>{display_name}</b>\n\n"
        f"{THIN_LINE}\n\n"
        f"🎯  Earn <b>{pct(bonus_pct)}</b> on every gold purchase\n"
        f"    made by users you refer.\n\n"
        f"🎁  <b>Your bonus is credited instantly.</b>\n"
        f"    No limits. No expiry.\n\n"
        f"{THIN_LINE}\n\n"
        f"🔗  <b>Your Referral Link:</b>\n"
        f"<code>{referral_link}</code>\n\n"
        f"📋  <b>Code:</b>  <code>{referral_code}</code>\n\n"
        f"{THIN_LINE}\n\n"
        f"💰  <b>Total Earned:</b>  <code>{usd(bonus_earned)}</code>\n\n"
        f"{THICK_LINE}\n\n"
        f"<i>Share your link and earn every time your friends buy gold!</i>"
    )


# ── Support ────────────────────────────────────────────────────────────────────

def support_message() -> str:
    return (
        f"{BRAND_HEADER}  ·  <b>Support</b>\n\n"
        f"{THICK_LINE}\n\n"
        f"🎖️  <b>Premium 24/7 Support</b>\n\n"
        f"{THIN_LINE}\n\n"
        f"⚡  <b>Average response:</b>   under 2 hours\n"
        f"🌍  <b>Languages:</b>          English · Arabic\n"
        f"🕐  <b>Hours:</b>              24 hours · 7 days\n\n"
        f"{THIN_LINE}\n\n"
        f"<i>When contacting support, please include your\n"
        f"<b>Order ID</b> or <b>Telegram username</b> for faster assistance.</i>"
    )


def faq_message() -> str:
    return (
        f"{BRAND_HEADER}  ·  <b>FAQ</b>\n\n"
        f"{THICK_LINE}\n\n"
        f"❓  <b>How long do payments take?</b>\n"
        f"    Crypto confirmations: <b>5 – 30 minutes</b>\n\n"
        f"❓  <b>When are sell orders processed?</b>\n"
        f"    Within <b>24 hours</b> on business days\n\n"
        f"❓  <b>What is the minimum purchase?</b>\n"
        f"    <b>0.1 gram</b> of gold\n\n"
        f"❓  <b>Is my gold insured?</b>\n"
        f"    Yes — all holdings are <b>fully backed & audited</b>\n\n"
        f"❓  <b>How does the referral program work?</b>\n"
        f"    Share your link · earn <b>1% on every purchase</b>\n"
        f"    your referrals make — credited instantly\n\n"
        f"❓  <b>Which cryptos are accepted?</b>\n"
        f"    <b>BTC · ETH · USDT</b> (and more via NOWPayments)\n\n"
        f"{THICK_LINE}"
    )
