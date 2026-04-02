from datetime import date
from pydantic import BaseModel


class NavHistoryResponse(BaseModel):
    id: int
    portfolio_id: int
    date: date
    total_nav: float
    nav_per_unit: float
    total_units: float
    benchmark_value: float | None

    model_config = {"from_attributes": True}
