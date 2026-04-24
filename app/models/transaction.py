import enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class TransactionType(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    REFERRAL_BONUS = "referral_bonus"
    ADMIN_CREDIT = "admin_credit"
    ADMIN_DEBIT = "admin_debit"
    def __str__(self): return self.value


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"
    def __str__(self): return self.value


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, values_callable=lambda obj: [e.value for e in obj]), nullable=False, index=True
    )
    amount_usd: Mapped[float] = mapped_column(Float, nullable=False)
    gold_grams: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, values_callable=lambda obj: [e.value for e in obj]), default=TransactionStatus.PENDING, nullable=False
    )

    reference_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Balance snapshots for audit trail
    balance_before_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    balance_after_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    gold_before: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    gold_after: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} type={self.transaction_type} amount=${self.amount_usd}>"
