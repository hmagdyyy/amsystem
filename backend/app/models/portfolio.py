from datetime import datetime, date
from sqlalchemy import Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    beginning_nav: Mapped[float] = mapped_column(Float, nullable=False)
    beginning_date: Mapped[date] = mapped_column(Date, nullable=False)
    current_nav: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_units: Mapped[float] = mapped_column(Float, nullable=False, default=1000.0)
    nav_per_unit: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    beginning_nav_per_unit: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    benchmark_ticker: Mapped[str | None] = mapped_column(String, nullable=True)
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("portfolios.id"), nullable=True)
    portfolio_type: Mapped[str] = mapped_column(String, nullable=False, default="standalone")  # standalone, parent, sub
    entity_type: Mapped[str] = mapped_column(String, nullable=False, default="fund")  # fund, client
    cash_balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fees_under_payment: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    dividends: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")
    cash_flows = relationship("CashFlow", back_populates="portfolio", cascade="all, delete-orphan")
    nav_history = relationship("NavHistory", back_populates="portfolio", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="portfolio", cascade="all, delete-orphan")
    upload_logs = relationship("UploadLog", back_populates="portfolio", cascade="all, delete-orphan")
    sub_portfolios = relationship("Portfolio", foreign_keys=[parent_id], lazy="select")
