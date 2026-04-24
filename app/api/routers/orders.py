from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import BotAuth, DbSession
from app.api.schemas.order import BuyOrderRequest, OrderResponse, SellOrderRequest
from app.models.order import OrderStatus
from app.services import order_service, payment_service, user_service

router = APIRouter()


@router.post("/buy", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_buy_order(payload: BuyOrderRequest, db: DbSession, _: BotAuth):
    """Initiate a gold buy order and return a payment invoice."""
    user = await user_service.get_user_by_telegram_id(db, payload.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Account suspended")

    order = await order_service.create_buy_order(
        db, user, payload.grams, payload.crypto_currency
    )

    # Create payment invoice
    try:
        invoice = await payment_service.create_payment(
            amount_usd=order.total_usd,
            crypto_currency=payload.crypto_currency,
            order_id=order.id,
        )
        order.payment_id = invoice.payment_id
        order.payment_url = invoice.payment_url
        order.payment_address = invoice.payment_address
        order.crypto_amount = invoice.pay_amount
        order.status = OrderStatus.AWAITING_PAYMENT
        await db.flush()
    except Exception as e:
        order.status = OrderStatus.FAILED
        await db.flush()
        raise HTTPException(status_code=502, detail=f"Payment gateway error: {e}") from e

    return order


@router.post("/sell", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_sell_order(payload: SellOrderRequest, db: DbSession, _: BotAuth):
    """Initiate a gold sell order (requires admin approval for payout)."""
    user = await user_service.get_user_by_telegram_id(db, payload.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Account suspended")

    try:
        order = await order_service.create_sell_order(
            db,
            user,
            payload.grams,
            payload.withdrawal_crypto,
            payload.withdrawal_wallet,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return order


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: DbSession, _: BotAuth):
    order = await order_service.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/user/{telegram_id}", response_model=list[OrderResponse])
async def get_user_orders(
    telegram_id: int,
    db: DbSession,
    _: BotAuth,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    user = await user_service.get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await order_service.get_user_orders(db, user.id, skip=skip, limit=limit)
