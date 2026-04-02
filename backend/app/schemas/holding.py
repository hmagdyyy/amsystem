from datetime import datetime
from pydantic import BaseModel


class HoldingResponse(BaseModel):
    id: int
    portfolio_id: int
    ticker: str
    name: str | None
    shares: float
    cost_per_share: float
    market_price: float
    market_value: float
    weight: float
    return_pct: float
    sector: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class HoldingUpdate(BaseModel):
    market_price: float | None = None
    shares: float | None = None
