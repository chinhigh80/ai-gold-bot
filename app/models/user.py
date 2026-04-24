import random
import string
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.transaction import Transaction
    from app.models.withdrawal import Withdrawal


def _generate_referral_code() -> str:
    chars = string.ascii_uppercase + string.digits
    return "GV-" + "".join(random.choices(chars, k=8))


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # Financials
    balance_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    gold_grams: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Referral
    referral_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, default=_generate_referral_code
    )
    referred_by_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    referral_bonus_earned_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user", lazy="select")
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="user", lazy="select"
    )
    withdrawals: Mapped[list["Withdrawal"]] = relationship(
        "Withdrawal", back_populates="user", lazy="select"
    )
    referred_users: Mapped[list["User"]] = relationship(
        "User",
        foreign_keys=[referred_by_id],
        lazy="select",
    )

    @property
    def display_name(self) -> str:
        if self.first_name:
            parts = [self.first_name]
            if self.last_name:
                parts.append(self.last_name)
            return " ".join(parts)
        return self.username or f"User#{self.telegram_id}"

    def __repr__(self) -> str:
        return f"<User id={self.id} telegram_id={self.telegram_id} username={self.username}>"
