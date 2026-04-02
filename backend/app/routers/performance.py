from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config import get_db
from app.models import Portfolio, NavHistory
from app.models.holding import Holding
from app.schemas.portfolio import PortfolioSummary
from app.schemas.cash_flow import CashFlowCreate, CashFlowResponse
from app.schemas.nav_history import NavHistoryResponse
from app.services.ic_engine import record_cash_flow, snapshot_nav, calculate_ytd_return
from app.services.benchmark import get_benchmark_ytd_return, get_benchmark_series

router = APIRouter(prefix="/api/performance", tags=["performance"])


@router.get("/summary", response_model=list[PortfolioSummary])
def dashboard_summary(db: Session = Depends(get_db)):
    portfolios = db.query(Portfolio).order_by(Portfolio.name).all()

    def build_summary(p: Portfolio, nav_override: float | None = None) -> PortfolioSummary:
        entity = getattr(p, "entity_type", "fund") or "fund"
        nav = nav_override if nav_override is not None else p.current_nav
        ytd = calculate_ytd_return(db, p.id)
        nav_return = round((nav / p.beginning_nav - 1) * 100, 2) if p.beginning_nav and p.beginning_nav > 0 else None
        bench_ret = get_benchmark_ytd_return(p.benchmark_ticker) if p.benchmark_ticker else None
        alpha = round(ytd - bench_ret, 2) if bench_ret is not None else None

        # Equity exposure
        if p.portfolio_type == "parent":
            member_ids = [s.id for s in p.sub_portfolios]
            holdings = db.query(Holding).filter(Holding.portfolio_id.in_(member_ids)).all() if member_ids else []
        else:
            holdings = db.query(Holding).filter(Holding.portfolio_id == p.id).all()
        equity_value = sum(h.market_value for h in holdings if h.holding_type == "equity")
        equity_exposure = round(equity_value / nav * 100, 2) if nav > 0 else 0.0

        return PortfolioSummary(
            id=p.id,
            name=p.name,
            beginning_nav=p.beginning_nav,
            current_nav=nav,
            nav_per_unit=p.nav_per_unit,
            entity_type=entity,
            ytd_return=ytd,
            nav_return=nav_return,
            equity_exposure=equity_exposure,
            benchmark_return=bench_ret,
            alpha=alpha,
            benchmark_ticker=p.benchmark_ticker,
            portfolio_type=p.portfolio_type or "standalone",
        )

    # Index members by cluster parent_id
    members_by_parent: dict[int, list[PortfolioSummary]] = {}
    for p in portfolios:
        if p.parent_id:
            members_by_parent.setdefault(p.parent_id, []).append(build_summary(p))

    # Build the list: all portfolios appear at top level
    # Clusters show aggregated NAV and their members as children
    result = []
    for p in portfolios:
        if p.portfolio_type == "parent":
            members = members_by_parent.get(p.id, [])
            agg_nav = sum(m.current_nav for m in members)
            summary = build_summary(p, nav_override=agg_nav)
            summary.children = members
            result.append(summary)
        else:
            result.append(build_summary(p))

    return result


@router.get("/{portfolio_id}/nav-history", response_model=list[NavHistoryResponse])
def get_nav_history(portfolio_id: int, db: Session = Depends(get_db)):
    return (
        db.query(NavHistory)
        .filter(NavHistory.portfolio_id == portfolio_id)
        .order_by(NavHistory.date.asc())
        .all()
    )


@router.get("/{portfolio_id}/chart-data")
def get_chart_data(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    nav_records = (
        db.query(NavHistory)
        .filter(NavHistory.portfolio_id == portfolio_id)
        .order_by(NavHistory.date.asc())
        .all()
    )

    if not nav_records:
        return {"portfolio": [], "benchmark": []}

    base_npu = nav_records[0].nav_per_unit
    portfolio_series = [
        {"date": r.date.isoformat(), "value": round(r.nav_per_unit / base_npu * 100, 2) if base_npu > 0 else 100}
        for r in nav_records
    ]

    benchmark_series = []
    if portfolio.benchmark_ticker:
        benchmark_series = get_benchmark_series(portfolio.benchmark_ticker)

    return {"portfolio": portfolio_series, "benchmark": benchmark_series}


@router.post("/cash-flow", response_model=CashFlowResponse)
def add_cash_flow(data: CashFlowCreate, db: Session = Depends(get_db)):
    try:
        cf = record_cash_flow(db, data.portfolio_id, data.date, data.type, data.amount)
        return cf
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{portfolio_id}/snapshot")
def take_snapshot(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    bench_val = None
    if portfolio.benchmark_ticker:
        from app.services.market_data import fetch_benchmark_level
        bench_val = fetch_benchmark_level(portfolio.benchmark_ticker)

    snap = snapshot_nav(db, portfolio_id, date.today(), bench_val)
    return NavHistoryResponse.model_validate(snap)
