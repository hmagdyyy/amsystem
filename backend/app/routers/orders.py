from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.config import get_db
from app.models import Order, Portfolio
from app.schemas.order import OrderCreate, QuickOrderCreate, OrderStatusUpdate, OrderResponse
from app.services.order_builder import build_order

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _enrich_order(order: Order, db: Session) -> OrderResponse:
    portfolio = db.query(Portfolio).filter(Portfolio.id == order.portfolio_id).first()
    resp = OrderResponse.model_validate(order)
    resp.portfolio_name = portfolio.name if portfolio else None
    return resp


@router.post("/", response_model=OrderResponse)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    try:
        order = build_order(db, data.portfolio_id, data.ticker, data.target_weight, data.price)
        return _enrich_order(order, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/quick", response_model=OrderResponse)
def quick_order(data: QuickOrderCreate, db: Session = Depends(get_db)):
    if data.price and data.price > 0:
        try:
            order = build_order(db, data.portfolio_id, data.ticker, data.target_weight, data.price)
            return _enrich_order(order, db)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    from app.services.market_data import fetch_price
    price = fetch_price(data.ticker)
    if not price:
        raise HTTPException(status_code=400, detail=f"Could not fetch price for {data.ticker}")
    try:
        order = build_order(db, data.portfolio_id, data.ticker, data.target_weight, price)
        return _enrich_order(order, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=list[OrderResponse])
def list_orders(portfolio_id: int | None = None, status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Order)
    if portfolio_id:
        q = q.filter(Order.portfolio_id == portfolio_id)
    if status:
        q = q.filter(Order.status == status)
    orders = q.order_by(Order.created_at.desc()).all()
    return [_enrich_order(o, db) for o in orders]


@router.put("/{order_id}/status", response_model=OrderResponse)
def update_order_status(order_id: int, data: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    valid_statuses = {"DRAFT", "PENDING", "SENT", "FILLED", "CANCELLED"}
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    order.status = data.status
    db.commit()
    db.refresh(order)
    return _enrich_order(order, db)


@router.delete("/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
    return {"detail": "Deleted"}


@router.get("/{order_id}/allocations")
def get_order_allocations(order_id: int, db: Session = Depends(get_db)):
    """For a parent (Omni) portfolio order, break down shares per sub-portfolio by NAV weight."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    parent = db.query(Portfolio).filter(Portfolio.id == order.portfolio_id).first()
    if not parent or parent.portfolio_type != "parent":
        raise HTTPException(status_code=400, detail="Allocations only available for parent portfolio orders")

    subs = db.query(Portfolio).filter(Portfolio.parent_id == parent.id).all()
    if not subs:
        return []

    total_nav = sum(s.current_nav for s in subs)
    if total_nav <= 0:
        return []

    allocations = []
    allocated_shares = 0
    for i, sub in enumerate(sorted(subs, key=lambda s: s.current_nav, reverse=True)):
        nav_weight = sub.current_nav / total_nav
        if i == len(subs) - 1:
            # Last sub-portfolio gets the remainder to avoid rounding gaps
            shares = order.shares - allocated_shares
        else:
            shares = int(round(order.shares * nav_weight))
            allocated_shares += shares

        allocations.append({
            "sub_portfolio_id": sub.id,
            "sub_portfolio_name": sub.name,
            "nav": sub.current_nav,
            "nav_weight_pct": round(nav_weight * 100, 2),
            "allocated_shares": shares,
            "notional": round(shares * order.price, 2),
        })

    return allocations


@router.get("/net-cash-flow")
def get_net_cash_flow(
    target_date: date | None = Query(None, description="Date to calculate for (defaults to today)"),
    db: Session = Depends(get_db),
):
    """Calculate net cash flow from orders per portfolio for a given day.

    BUY = cash outflow (negative), SELL = cash inflow (positive).
    Excludes CANCELLED orders.
    """
    d = target_date or date.today()

    # Get all non-cancelled orders created on the target date
    # Use datetime range to avoid SQLite cast issues
    day_start = datetime(d.year, d.month, d.day, 0, 0, 0)
    day_end = datetime(d.year, d.month, d.day, 23, 59, 59, 999999)
    orders = (
        db.query(Order)
        .filter(
            Order.created_at >= day_start,
            Order.created_at <= day_end,
            Order.status != "CANCELLED",
        )
        .all()
    )

    # Group by portfolio
    portfolio_ids = {o.portfolio_id for o in orders}
    portfolios = {
        p.id: p
        for p in db.query(Portfolio).filter(Portfolio.id.in_(portfolio_ids)).all()
    } if portfolio_ids else {}

    # Calculate per portfolio
    per_portfolio: dict[int, dict] = {}
    for o in orders:
        if o.portfolio_id not in per_portfolio:
            p = portfolios.get(o.portfolio_id)
            per_portfolio[o.portfolio_id] = {
                "portfolio_id": o.portfolio_id,
                "portfolio_name": p.name if p else "Unknown",
                "current_nav": p.current_nav if p else 0.0,
                "buys": 0.0,
                "sells": 0.0,
                "buy_orders": 0,
                "sell_orders": 0,
                "orders": [],
            }
        entry = per_portfolio[o.portfolio_id]
        if o.side == "BUY":
            entry["buys"] += o.notional_amount
            entry["buy_orders"] += 1
        else:
            entry["sells"] += o.notional_amount
            entry["sell_orders"] += 1
        entry["orders"].append({
            "id": o.id,
            "ticker": o.ticker,
            "side": o.side,
            "shares": o.shares,
            "price": o.price,
            "notional": o.notional_amount,
            "status": o.status,
        })

    # Build result
    rows = []
    for entry in sorted(per_portfolio.values(), key=lambda e: abs(e["buys"] - e["sells"]), reverse=True):
        net = entry["sells"] - entry["buys"]  # positive = net inflow, negative = net outflow
        nav = entry["current_nav"]
        rows.append({
            "portfolio_id": entry["portfolio_id"],
            "portfolio_name": entry["portfolio_name"],
            "current_nav": round(nav, 2),
            "buys": round(entry["buys"], 2),
            "sells": round(entry["sells"], 2),
            "net_cash_flow": round(net, 2),
            "net_cash_flow_pct": round(net / nav * 100, 2) if nav > 0 else 0.0,
            "buy_orders": entry["buy_orders"],
            "sell_orders": entry["sell_orders"],
            "orders": entry["orders"],
        })

    total_buys = sum(r["buys"] for r in rows)
    total_sells = sum(r["sells"] for r in rows)
    total_nav = sum(r["current_nav"] for r in rows)
    total_net = total_sells - total_buys

    return {
        "date": d.isoformat(),
        "total_buys": round(total_buys, 2),
        "total_sells": round(total_sells, 2),
        "total_net_cash_flow": round(total_net, 2),
        "total_net_cash_flow_pct": round(total_net / total_nav * 100, 2) if total_nav > 0 else 0.0,
        "portfolios": rows,
    }
