from fastapi import APIRouter, HTTPException, status

from app.api.deps import BotAuth, DbSession
from app.api.schemas.withdrawal import WithdrawalRequest, WithdrawalResponse
from app.services import user_service, withdrawal_service

router = APIRouter()


@router.post("/", response_model=WithdrawalResponse, status_code=status.HTTP_201_CREATED)
async def request_withdrawal(payload: WithdrawalRequest, db: DbSession, _: BotAuth):
    """Submit a gold withdrawal request for admin approval."""
    user = await user_service.get_user_by_telegram_id(db, payload.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Account suspended")

    try:
        withdrawal = await withdrawal_service.create_withdrawal_request(
            db,
            user,
            grams=payload.grams,
            crypto_type=payload.crypto_type,
            wallet_address=payload.wallet_address,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return withdrawal


@router.get("/user/{telegram_id}", response_model=list[WithdrawalResponse])
async def get_user_withdrawals(telegram_id: int, db: DbSession, _: BotAuth):
    user = await user_service.get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await withdrawal_service.get_user_withdrawals(db, user.id)


@router.get("/{withdrawal_id}", response_model=WithdrawalResponse)
async def get_withdrawal(withdrawal_id: int, db: DbSession, _: BotAuth):
    from sqlalchemy import select
    from app.models.withdrawal import Withdrawal
    result = await db.execute(select(Withdrawal).where(Withdrawal.id == withdrawal_id))
    w = result.scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    return w
