from datetime import datetime
from pydantic import BaseModel


class OrderCreate(BaseModel):
    portfolio_id: int
    ticker: str
    target_weight: float
    price: float


class QuickOrderCreate(BaseModel):
    portfolio_id: int
    ticker: str
    side: str  # BUY or SELL
    target_weight: float
    price: float | None = None


class OrderStatusUpdate(BaseModel):
    status: str  # DRAFT, PENDING, SENT, FILLED, CANCELLED


class OrderResponse(BaseModel):
    id: int
    portfolio_id: int
    ticker: str
    side: str
    target_weight: float
    current_weight: float
    shares: int
    price: float
    notional_amount: float
    status: str
    bloomberg_message: str | None
    created_at: datetime
    updated_at: datetime
    portfolio_name: str | None = None

    model_config = {"from_attributes": True}
