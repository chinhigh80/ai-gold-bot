import enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class WithdrawalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"
    def __str__(self): return self.value


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Amount
    amount_usd: Mapped[float] = mapped_column(Float, nullable=False)
    gold_grams: Mapped[float] = mapped_column(Float, nullable=False)

    # Crypto details
    crypto_type: Mapped[str] = mapped_column(String(20), nullable=False)
    wallet_address: Mapped[str] = mapped_column(String(255), nullable=False)
    crypto_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    crypto_price_at_request: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Gold price at time of request
    gold_price_per_gram_usd: Mapped[float] = mapped_column(Float, nullable=False)
    spread_percent: Mapped[float] = mapped_column(Float, nullable=False)

    # Status
    status: Mapped[WithdrawalStatus] = mapped_column(
        Enum(WithdrawalStatus, values_callable=lambda obj: [e.value for e in obj]), default=WithdrawalStatus.PENDING, nullable=False, index=True
    )

    # Admin
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tx_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="withdrawals")

    def __repr__(self) -> str:
        return f"<Withdrawal id={self.id} amount=${self.amount_usd} status={self.status}>"
