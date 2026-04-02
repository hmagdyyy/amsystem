from datetime import date
from sqlalchemy.orm import Session
from app.models import Portfolio, CashFlow, NavHistory


def record_cash_flow(db: Session, portfolio_id: int, flow_date: date, flow_type: str, amount: float) -> CashFlow:
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise ValueError(f"Portfolio {portfolio_id} not found")

    # Auto-initialize nav_per_unit for portfolios that don't have it yet
    if portfolio.nav_per_unit <= 0:
        if portfolio.current_nav > 0 and portfolio.total_units > 0:
            portfolio.nav_per_unit = portfolio.current_nav / portfolio.total_units
        elif portfolio.current_nav > 0:
            portfolio.total_units = 1000.0
            portfolio.nav_per_unit = portfolio.current_nav / 1000.0
        else:
            raise ValueError("Portfolio must have a positive NAV before recording cash flows")

    # IC method: find how many units (ICs) the cash flow represents at today's price
    units_changed = amount / portfolio.nav_per_unit

    if flow_type == "INJECTION":
        portfolio.total_units += units_changed
        portfolio.current_nav += amount
    elif flow_type == "WITHDRAWAL":
        if units_changed > portfolio.total_units:
            raise ValueError("Withdrawal exceeds total units")
        if amount > portfolio.current_nav:
            raise ValueError("Withdrawal exceeds current NAV")
        portfolio.total_units -= units_changed
        portfolio.current_nav -= amount
    else:
        raise ValueError(f"Invalid flow type: {flow_type}")

    # nav_per_unit stays the same — cash flows don't change the IC price
    cf = CashFlow(
        portfolio_id=portfolio_id,
        date=flow_date,
        type=flow_type,
        amount=amount,
        units_changed=units_changed,
        nav_per_unit_at_flow=portfolio.nav_per_unit,
    )
    db.add(cf)
    db.commit()
    db.refresh(cf)
    return cf


def snapshot_nav(db: Session, portfolio_id: int, snap_date: date, benchmark_value: float | None = None) -> NavHistory:
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise ValueError(f"Portfolio {portfolio_id} not found")

    existing = (
        db.query(NavHistory)
        .filter(NavHistory.portfolio_id == portfolio_id, NavHistory.date == snap_date)
        .first()
    )

    if existing:
        existing.total_nav = portfolio.current_nav
        existing.nav_per_unit = portfolio.nav_per_unit
        existing.total_units = portfolio.total_units
        existing.benchmark_value = benchmark_value
        db.commit()
        db.refresh(existing)
        return existing

    nav = NavHistory(
        portfolio_id=portfolio_id,
        date=snap_date,
        total_nav=portfolio.current_nav,
        nav_per_unit=portfolio.nav_per_unit,
        total_units=portfolio.total_units,
        benchmark_value=benchmark_value,
    )
    db.add(nav)
    db.commit()
    db.refresh(nav)
    return nav


def calculate_ytd_return(db: Session, portfolio_id: int) -> float:
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise ValueError(f"Portfolio {portfolio_id} not found")

    if portfolio.nav_per_unit <= 0:
        return 0.0

    # Priority 1: Use NAV history snapshots from year start
    year_start = date(date.today().year, 1, 1)
    start_snap = (
        db.query(NavHistory)
        .filter(NavHistory.portfolio_id == portfolio_id, NavHistory.date >= year_start)
        .order_by(NavHistory.date.asc())
        .first()
    )

    if start_snap and start_snap.nav_per_unit > 0:
        return round((portfolio.nav_per_unit / start_snap.nav_per_unit - 1) * 100, 2)

    # Priority 2: Use beginning_nav_per_unit if set
    if portfolio.beginning_nav_per_unit > 0:
        return round((portfolio.nav_per_unit / portfolio.beginning_nav_per_unit - 1) * 100, 2)

    return 0.0
