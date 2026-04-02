from datetime import datetime
from sqlalchemy import Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config import Base


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(Integer, ForeignKey("portfolios.id"), nullable=False)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    shares: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cost_per_share: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    market_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    market_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    return_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sector: Mapped[str | None] = mapped_column(String, nullable=True)
    holding_type: Mapped[str] = mapped_column(String, nullable=False, default="equity")  # "equity" or "fund"
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="holdings")
