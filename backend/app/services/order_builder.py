import math
from sqlalchemy.orm import Session
from app.models import Portfolio, Holding, Order


def build_order(db: Session, portfolio_id: int, ticker: str, target_weight: float, price: float) -> Order:
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise ValueError(f"Portfolio {portfolio_id} not found")

    # For clusters, build orders for each member and return the first as the "parent" order
    if portfolio.portfolio_type == "parent":
        return _build_cluster_orders(db, portfolio, ticker, target_weight, price)

    return _build_single_order(db, portfolio, ticker, target_weight, price)


def _build_single_order(db: Session, portfolio: Portfolio, ticker: str, target_weight: float, price: float) -> Order:
    if portfolio.current_nav <= 0:
        raise ValueError("Portfolio NAV must be positive")

    holding = (
        db.query(Holding)
        .filter(Holding.portfolio_id == portfolio.id, Holding.ticker == ticker.upper())
        .first()
    )

    current_value = holding.market_value if holding else 0.0
    current_weight = (current_value / portfolio.current_nav * 100) if portfolio.current_nav > 0 else 0.0

    target_value = portfolio.current_nav * (target_weight / 100)
    delta_value = target_value - current_value

    if price <= 0:
        raise ValueError("Price must be positive")

    shares = int(math.floor(abs(delta_value) / price))
    side = "BUY" if delta_value >= 0 else "SELL"
    notional = shares * price

    bloomberg_msg = f"{side} {shares} {ticker.upper()} @ {price:.2f} ({portfolio.name})"

    order = Order(
        portfolio_id=portfolio.id,
        ticker=ticker.upper(),
        side=side,
        target_weight=round(target_weight, 2),
        current_weight=round(current_weight, 2),
        shares=shares,
        price=price,
        notional_amount=round(notional, 2),
        status="DRAFT",
        bloomberg_message=bloomberg_msg,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def _build_cluster_orders(db: Session, cluster: Portfolio, ticker: str, target_weight: float, price: float) -> Order:
    """Build individual orders for each member of a cluster, allocated by NAV weight."""
    members = db.query(Portfolio).filter(Portfolio.parent_id == cluster.id).all()
    if not members:
        raise ValueError("Cluster has no member portfolios")

    if price <= 0:
        raise ValueError("Price must be positive")

    orders = []
    for member in members:
        if member.current_nav <= 0:
            continue

        holding = (
            db.query(Holding)
            .filter(Holding.portfolio_id == member.id, Holding.ticker == ticker.upper())
            .first()
        )

        current_value = holding.market_value if holding else 0.0
        current_weight = (current_value / member.current_nav * 100) if member.current_nav > 0 else 0.0

        target_value = member.current_nav * (target_weight / 100)
        delta_value = target_value - current_value

        shares = int(math.floor(abs(delta_value) / price))
        side = "BUY" if delta_value >= 0 else "SELL"
        notional = shares * price

        if shares == 0:
            continue

        bloomberg_msg = f"{side} {shares} {ticker.upper()} @ {price:.2f} ({member.name})"

        order = Order(
            portfolio_id=member.id,
            ticker=ticker.upper(),
            side=side,
            target_weight=round(target_weight, 2),
            current_weight=round(current_weight, 2),
            shares=shares,
            price=price,
            notional_amount=round(notional, 2),
            status="DRAFT",
            bloomberg_message=bloomberg_msg,
        )
        db.add(order)
        orders.append(order)

    if not orders:
        raise ValueError("No orders generated — all member allocations resulted in 0 shares")

    db.commit()
    for o in orders:
        db.refresh(o)

    return orders[0]


def generate_bloomberg_message(order: Order, portfolio_name: str) -> str:
    return f"{order.side} {order.shares} {order.ticker} @ {order.price:.2f} ({portfolio_name})"
