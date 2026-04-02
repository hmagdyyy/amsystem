from datetime import datetime
from sqlalchemy import Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(Integer, ForeignKey("portfolios.id"), nullable=False)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    side: Mapped[str] = mapped_column(String, nullable=False)  # BUY or SELL
    target_weight: Mapped[float] = mapped_column(Float, nullable=False)
    current_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    shares: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    notional_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="DRAFT")
    bloomberg_message: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="orders")
