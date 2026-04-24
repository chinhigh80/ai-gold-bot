import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class OrderType(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"
    def __str__(self): return self.value


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    AWAITING_PAYMENT = "awaiting_payment"
    PRICE_LOCKED = "price_locked"
    PAID = "paid"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    EXPIRED = "expired"
    def __str__(self): return self.value


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Trade details
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    grams: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_gram_usd: Mapped[float] = mapped_column(Float, nullable=False)
    base_price_per_gram_usd: Mapped[float] = mapped_column(Float, nullable=False)
    total_usd: Mapped[float] = mapped_column(Float, nullable=False)
    markup_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    spread_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Status
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, values_callable=lambda obj: [e.value for e in obj]), default=OrderStatus.PENDING, nullable=False, index=True
    )

    # Payment
    payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    payment_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    payment_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    crypto_currency: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    crypto_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Price lock
    price_locked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    price_lock_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Sell-specific: withdrawal info
    withdrawal_crypto: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    withdrawal_wallet: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Admin notes
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="orders")

    def __repr__(self) -> str:
        return f"<Order id={self.id} type={self.order_type} status={self.status} grams={self.grams}>"
