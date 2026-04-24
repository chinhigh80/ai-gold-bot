from sqlalchemy import BigInteger, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PriceLog(Base):
    __tablename__ = "price_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    price_per_oz_usd: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_gram_usd: Mapped[float] = mapped_column(Float, nullable=False)
    aed_usd_rate: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="goldapi")

    def __repr__(self) -> str:
        return f"<PriceLog id={self.id} price_per_gram=${self.price_per_gram_usd}>"
