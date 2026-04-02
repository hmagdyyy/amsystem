from datetime import datetime
from pydantic import BaseModel


class UploadLogResponse(BaseModel):
    id: int
    portfolio_id: int | None
    filename: str
    uploaded_at: datetime
    records_processed: int
    status: str

    model_config = {"from_attributes": True}


class UploadResult(BaseModel):
    portfolios_updated: int
    total_holdings: int
    logs: list[UploadLogResponse]
