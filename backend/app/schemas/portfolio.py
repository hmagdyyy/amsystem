from datetime import date, datetime
from pydantic import BaseModel


class PortfolioCreate(BaseModel):
    name: str
    beginning_nav: float
    beginning_date: date
    beginning_nav_per_unit: float = 0.0
    benchmark_ticker: str | None = None
    entity_type: str = "fund"  # fund or client


class ClusterCreate(BaseModel):
    name: str
    benchmark_ticker: str | None = None


class PortfolioUpdate(BaseModel):
    name: str | None = None
    beginning_nav: float | None = None
    beginning_nav_per_unit: float | None = None
    benchmark_ticker: str | None = None
    entity_type: str | None = None


class PortfolioResponse(BaseModel):
    id: int
    name: str
    beginning_nav: float
    beginning_date: date
    current_nav: float
    total_units: float
    nav_per_unit: float
    beginning_nav_per_unit: float
    benchmark_ticker: str | None
    parent_id: int | None = None
    portfolio_type: str = "standalone"
    entity_type: str = "fund"
    cash_balance: float = 0.0
    fees_under_payment: float = 0.0
    dividends: float = 0.0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PortfolioSummary(BaseModel):
    id: int
    name: str
    beginning_nav: float
    current_nav: float
    nav_per_unit: float
    entity_type: str = "fund"
    ytd_return: float
    nav_return: float | None
    equity_exposure: float = 0.0
    benchmark_return: float | None
    alpha: float | None
    benchmark_ticker: str | None
    portfolio_type: str = "standalone"
    children: list["PortfolioSummary"] = []

    model_config = {"from_attributes": True}
