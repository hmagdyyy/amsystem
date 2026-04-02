from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config import get_db
from app.models import Holding, Portfolio
from app.schemas.holding import HoldingResponse

router = APIRouter(prefix="/api/holdings", tags=["holdings"])


def _get_all_holdings(portfolio_id: int, db: Session) -> list[Holding]:
    """Get holdings for a portfolio. For parent portfolios, aggregate from all children."""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        return []

    if portfolio.portfolio_type == "parent":
        child_ids = [
            c.id for c in db.query(Portfolio.id).filter(Portfolio.parent_id == portfolio_id).all()
        ]
        if not child_ids:
            return []
        return db.query(Holding).filter(Holding.portfolio_id.in_(child_ids)).all()
    else:
        return db.query(Holding).filter(Holding.portfolio_id == portfolio_id).all()


def _consolidate_holdings(holdings: list[Holding], parent_nav: float) -> list[dict]:
    """Consolidate holdings by ticker, summing shares and market values."""
    by_ticker: dict[str, dict] = {}
    for h in holdings:
        key = h.ticker
        if key not in by_ticker:
            by_ticker[key] = {
                "id": h.id,
                "portfolio_id": h.portfolio_id,
                "ticker": h.ticker,
                "name": h.name,
                "shares": 0.0,
                "total_cost": 0.0,
                "market_price": h.market_price,
                "market_value": 0.0,
                "weight": 0.0,
                "sector": h.sector,
                "holding_type": getattr(h, "holding_type", None),
                "updated_at": h.updated_at,
            }
        entry = by_ticker[key]
        entry["shares"] += h.shares
        entry["total_cost"] += h.shares * h.cost_per_share
        entry["market_value"] += h.market_value
        # Keep the latest market_price
        entry["market_price"] = h.market_price

    result = []
    for entry in by_ticker.values():
        entry["cost_per_share"] = entry["total_cost"] / entry["shares"] if entry["shares"] > 0 else 0
        entry["weight"] = round(entry["market_value"] / parent_nav * 100, 2) if parent_nav > 0 else 0
        entry["return_pct"] = round((entry["market_price"] / entry["cost_per_share"] - 1) * 100, 2) if entry["cost_per_share"] > 0 else 0
        del entry["total_cost"]
        result.append(entry)

    result.sort(key=lambda x: x["weight"], reverse=True)
    return result


@router.get("/portfolio/{portfolio_id}", response_model=list[HoldingResponse])
def get_holdings(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()

    if portfolio and portfolio.portfolio_type == "parent":
        holdings = _get_all_holdings(portfolio_id, db)
        return _consolidate_holdings(holdings, portfolio.current_nav)

    return (
        db.query(Holding)
        .filter(Holding.portfolio_id == portfolio_id)
        .order_by(Holding.weight.desc())
        .all()
    )


@router.get("/portfolio/{portfolio_id}/sectors")
def get_sector_breakdown(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()

    if portfolio and portfolio.portfolio_type == "parent":
        holdings = _get_all_holdings(portfolio_id, db)
        consolidated = _consolidate_holdings(holdings, portfolio.current_nav)
        sectors: dict[str, float] = {}
        for h in consolidated:
            sector = h.get("sector") or "Unknown"
            sectors[sector] = sectors.get(sector, 0) + h["weight"]
        return [{"sector": k, "weight": round(v, 2)} for k, v in sorted(sectors.items(), key=lambda x: -x[1])]

    holdings = db.query(Holding).filter(Holding.portfolio_id == portfolio_id).all()
    sectors: dict[str, float] = {}
    for h in holdings:
        sector = h.sector or "Unknown"
        sectors[sector] = sectors.get(sector, 0) + h.weight
    return [{"sector": k, "weight": round(v, 2)} for k, v in sorted(sectors.items(), key=lambda x: -x[1])]
