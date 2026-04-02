from datetime import date
from sqlalchemy import Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config import Base


class CashFlow(Base):
    __tablename__ = "cash_flows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(Integer, ForeignKey("portfolios.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # INJECTION or WITHDRAWAL
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    units_changed: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    nav_per_unit_at_flow: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    portfolio = relationship("Portfolio", back_populates="cash_flows")
