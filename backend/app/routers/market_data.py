from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config import get_db
from app.models import Portfolio, Holding
from app.services.market_data import refresh_portfolio_prices, fetch_price
from app.schemas.holding import HoldingResponse

router = APIRouter(prefix="/api/market-data", tags=["market-data"])


@router.post("/refresh/{portfolio_id}")
def refresh_prices(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    updated = refresh_portfolio_prices(db, portfolio_id)
    return {"updated": updated, "portfolio_nav": portfolio.current_nav}


@router.post("/refresh-all")
def refresh_all_prices(db: Session = Depends(get_db)):
    portfolios = db.query(Portfolio).all()
    total_updated = 0
    for p in portfolios:
        total_updated += refresh_portfolio_prices(db, p.id)
    return {"total_updated": total_updated}


@router.get("/price/{ticker}")
def get_price(ticker: str):
    price = fetch_price(ticker.upper())
    if price is None:
        raise HTTPException(status_code=404, detail=f"Could not fetch price for {ticker}")
    return {"ticker": ticker.upper(), "price": price}


@router.get("/rebalance/{portfolio_id}")
def rebalance_view(portfolio_id: int, db: Session = Depends(get_db)):
    holdings = (
        db.query(Holding)
        .filter(Holding.portfolio_id == portfolio_id)
        .order_by(Holding.weight.desc())
        .all()
    )
    return [
        {
            "ticker": h.ticker,
            "name": h.name,
            "current_weight": h.weight,
            "market_value": h.market_value,
            "shares": h.shares,
        }
        for h in holdings
    ]
