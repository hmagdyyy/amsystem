from datetime import date
from pydantic import BaseModel


class CashFlowCreate(BaseModel):
    portfolio_id: int
    date: date
    type: str  # INJECTION or WITHDRAWAL
    amount: float


class CashFlowResponse(BaseModel):
    id: int
    portfolio_id: int
    date: date
    type: str
    amount: float
    units_changed: float
    nav_per_unit_at_flow: float

    model_config = {"from_attributes": True}
