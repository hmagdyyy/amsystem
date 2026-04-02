import io
import csv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.config import get_db
from app.models import Portfolio, Holding, Order

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/holdings/{portfolio_id}")
def export_holdings_csv(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    holdings = db.query(Holding).filter(Holding.portfolio_id == portfolio_id).order_by(Holding.weight.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Ticker", "Name", "Shares", "Cost/Share", "Market Price", "Market Value", "Weight %", "Return %", "Sector"])
    for h in holdings:
        writer.writerow([h.ticker, h.name or "", h.shares, h.cost_per_share, h.market_price, h.market_value, h.weight, h.return_pct, h.sector or ""])

    output.seek(0)
    filename = f"{portfolio.name}_holdings.csv"
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/orders")
def export_orders_csv(portfolio_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Order)
    if portfolio_id:
        q = q.filter(Order.portfolio_id == portfolio_id)
    orders = q.order_by(Order.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Portfolio ID", "Ticker", "Side", "Shares", "Price", "Notional", "Target Weight %", "Current Weight %", "Status", "Bloomberg Message", "Created"])
    for o in orders:
        writer.writerow([o.portfolio_id, o.ticker, o.side, o.shares, o.price, o.notional_amount, o.target_weight, o.current_weight, o.status, o.bloomberg_message or "", o.created_at.isoformat()])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=orders.csv"},
    )
