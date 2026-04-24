from fastapi import APIRouter, HTTPException, status

from app.api.deps import BotAuth, DbSession
from app.api.schemas.user import UserCreate, UserResponse, UserUpdate, WalletResponse
from app.services import price_service, user_service

router = APIRouter()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_or_get_user(payload: UserCreate, db: DbSession, _: BotAuth):
    """Register a new user or return existing. Called by bot on /start."""
    user, created = await user_service.get_or_create_user(
        db,
        telegram_id=payload.telegram_id,
        username=payload.username,
        first_name=payload.first_name,
        last_name=payload.last_name,
        language_code=payload.language_code,
        referral_code=payload.referral_code,
    )
    return user


@router.get("/{telegram_id}", response_model=UserResponse)
async def get_user(telegram_id: int, db: DbSession, _: BotAuth):
    user = await user_service.get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/{telegram_id}/wallet", response_model=WalletResponse)
async def get_wallet(telegram_id: int, db: DbSession, _: BotAuth):
    user = await user_service.get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        price_data = await price_service.get_gold_price()
        gold_value = round(user.gold_grams * price_data.price_per_gram_usd, 2)
    except Exception:
        gold_value = 0.0

    return WalletResponse(
        telegram_id=user.telegram_id,
        display_name=user.display_name,
        balance_usd=user.balance_usd,
        gold_grams=user.gold_grams,
        gold_value_usd=gold_value,
        referral_code=user.referral_code,
        referral_bonus_earned_usd=user.referral_bonus_earned_usd,
    )


@router.patch("/{telegram_id}", response_model=UserResponse)
async def update_user(telegram_id: int, payload: UserUpdate, db: DbSession, _: BotAuth):
    user = await user_service.get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    await db.flush()
    return user
