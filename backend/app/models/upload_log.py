from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config import Base


class UploadLog(Base):
    __tablename__ = "upload_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("portfolios.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="SUCCESS")

    portfolio = relationship("Portfolio", back_populates="upload_logs")
