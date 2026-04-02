from datetime import date
from sqlalchemy import Integer, Float, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config import Base


class NavHistory(Base):
    __tablename__ = "nav_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(Integer, ForeignKey("portfolios.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    total_nav: Mapped[float] = mapped_column(Float, nullable=False)
    nav_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    total_units: Mapped[float] = mapped_column(Float, nullable=False)
    benchmark_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (UniqueConstraint("portfolio_id", "date", name="uq_portfolio_date"),)

    portfolio = relationship("Portfolio", back_populates="nav_history")
