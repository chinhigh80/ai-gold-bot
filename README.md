# ✨ AMIRA GOLD LUXURY — Telegram Gold Trading Bot

> Production-ready Telegram bot for buying and selling physical gold using real-time market prices and crypto payments (NOWPayments).

---

## 📐 Architecture

```
gold-bot/
├── app/
│   ├── config.py              # Settings (pydantic-settings + Redis runtime overrides)
│   ├── db/                    # SQLAlchemy async engine + Redis client
│   ├── models/                # ORM models: User, Order, Transaction, Withdrawal
│   ├── services/              # Business logic: price engine, orders, payments, images
│   ├── api/                   # FastAPI — REST API + NOWPayments webhook
│   ├── admin/                 # Jinja2 admin panel (dashboard, users, orders, settings)
│   ├── bot/                   # Aiogram 3.x Telegram bot
│   │   ├── handlers/          # start, buy, sell, wallet, transactions, support, referral
│   │   ├── keyboards/         # Inline keyboard factories
│   │   ├── middlewares/       # Rate limit, DB session, user registration
│   │   └── states/            # FSM states (BuyGold, SellGold)
│   └── worker/                # Celery tasks + RedBeat scheduler
├── migrations/                # Alembic async migrations
├── docker/                    # Per-service Dockerfiles
├── scripts/                   # create_admin.py, seed_data.py
├── docker-compose.yml
└── .env.example
```

**Services:** `api` · `bot` · `worker` · `beat` · `db (PostgreSQL 16)` · `redis` · `flower`

---

## 🚀 Deployment on Remote Server

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd gold-bot
```

### 2. Configure environment

```bash
cp .env.example .env
nano .env   # fill in all required values (see below)
```

### 3. Build and start

```bash
make build
make up
```

### 4. Run database migrations

```bash
make migrate
```

### 5. Create admin user

```bash
make create-admin
```

### 6. Access

| Service       | URL                              |
|---------------|----------------------------------|
| Admin Panel   | http://your-server:8000/admin    |
| API Docs      | http://your-server:8000/api/docs |
| Celery Flower | http://your-server:5555          |

> **Tip:** Put Nginx in front of port 8000 with SSL for production. Set `WEBHOOK_HOST=https://yourdomain.com` to use webhook mode instead of polling.

---

## 🔑 Required Configuration

| Variable | Where to get | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) | ✅ Yes |
| `ADMIN_TELEGRAM_IDS` | [@userinfobot](https://t.me/userinfobot) | ✅ Yes |
| `NOWPAYMENTS_API_KEY` | [nowpayments.io](https://nowpayments.io) | For crypto payments |
| `NOWPAYMENTS_IPN_SECRET` | NOWPayments dashboard | For payment webhooks |
| `NOWPAYMENTS_CALLBACK_URL` | Your public HTTPS domain | For payment webhooks |
| `GOLD_API_KEY` | [goldapi.io](https://www.goldapi.io) | Optional — free Swissquote fallback built in |
| `EXCHANGE_RATE_API_KEY` | [exchangerate-api.com](https://www.exchangerate-api.com) | Optional — fallback rate used |
| `POSTGRES_PASSWORD` | Your choice | ✅ Yes (change default) |
| `SECRET_KEY` | Random 64-char string | ✅ Yes |
| `JWT_SECRET` | Random 64-char string | ✅ Yes |
| `ADMIN_PASSWORD` | Your choice | ✅ Yes (change default) |

---

## 💰 Price Engine

- **Primary source:** GoldAPI.io (XAU/USD) — requires API key
- **Automatic fallback:** Swissquote public feed — free, no key needed
- **Cached in Redis** for `PRICE_CACHE_TTL` seconds (default 60s)
- **Price locked** for `PRICE_LOCK_DURATION` seconds on order creation (default 5 min)

```
Buy Price  = spot_price_per_gram × (1 + MARKUP_PERCENT / 100)
Sell Price = spot_price_per_gram × (1 − SPREAD_PERCENT / 100)
```

---

## 🤖 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome screen + main menu |
| `/buy` | Buy gold (preset or custom grams) |
| `/sell` | Sell gold → crypto payout |
| `/wallet` | View gold holdings |
| `/transactions` | Order history |
| `/referral` | Referral code & earnings |
| `/support` | Contact support |
| `/help` | Command list |

---

## 🧑‍💼 Admin Panel

- **Dashboard** — Live gold price, revenue stats, pending receipts
- **Users** — List, ban/unban, credit gold/balance manually
- **Orders** — All orders; ✅ Credit Gold for buy orders, wallet address for sell orders
- **Withdrawals** — Full wallet address display, one-click complete with TX hash
- **Settings** — All configurable at runtime (no restart needed):
  - Buy markup %, sell spread %, min buy/sell grams, referral bonus
  - NOWPayments API key, IPN secret, callback URL
  - GoldAPI & ExchangeRate API keys
  - Admin Telegram IDs, supported cryptos
  - Bot welcome image (upload from machine)
  - Admin password change
- **Broadcast** — Send text/photo/photo+text to all active users

---

## ⚙️ Runtime Settings

All settings in the Admin Panel take effect **immediately** — stored in Redis, read at call time. No restart required. Settings survive container restarts.

---

## ⚙️ Background Jobs (Celery)

| Task | Schedule |
|------|----------|
| `refresh_gold_price` | Every 60 seconds |
| `poll_pending_payments` | Every 2 minutes |
| `expire_stale_orders` | Every 10 minutes |
| `daily_price_broadcast` | Daily at 09:00 UTC |

---

## 🔐 Security

- All secrets via environment variables
- Rate limiting per user (Redis-backed)
- NOWPayments IPN signature verification (HMAC-SHA512)
- JWT admin authentication (httpOnly cookies, 24h expiry)
- Banned users blocked at middleware level

---

## 🐳 Docker Commands

```bash
make build          # Build all images
make up             # Start all services (detached)
make down           # Stop all services
make logs           # Tail all logs
make logs-bot       # Tail bot logs only
make migrate        # Run DB migrations
make create-admin   # Create admin user
make restart-bot    # Restart bot container
make restart-api    # Restart API container
make shell-api      # Shell into API container
make shell-db       # PostgreSQL shell
```

---

*Built with Python 3.11 · aiogram 3 · FastAPI · SQLAlchemy 2 · Celery · PostgreSQL 16 · Redis 7*
