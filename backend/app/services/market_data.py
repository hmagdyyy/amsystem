import yfinance as yf
from sqlalchemy.orm import Session
from app.models import Holding, Portfolio


def fetch_price(ticker: str) -> float | None:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


def fetch_ticker_info(ticker: str) -> dict:
    try:
        t = yf.Ticker(ticker)
        info = t.info
        return {
            "sector": info.get("sector"),
            "name": info.get("shortName") or info.get("longName"),
        }
    except Exception:
        return {}


def refresh_portfolio_prices(db: Session, portfolio_id: int) -> int:
    holdings = db.query(Holding).filter(Holding.portfolio_id == portfolio_id).all()
    updated = 0

    for holding in holdings:
        price = fetch_price(holding.ticker)
        if price is not None:
            holding.market_price = price
            holding.market_value = holding.shares * price
            holding.return_pct = round(((price - holding.cost_per_share) / holding.cost_per_share * 100), 2) if holding.cost_per_share > 0 else 0.0

            info = fetch_ticker_info(holding.ticker)
            if info.get("sector"):
                holding.sector = info["sector"]
            if info.get("name") and not holding.name:
                holding.name = info["name"]

            updated += 1

    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if portfolio:
        total_nav = sum(h.market_value for h in holdings)
        portfolio.current_nav = total_nav
        if portfolio.total_units > 0:
            portfolio.nav_per_unit = total_nav / portfolio.total_units

        for h in holdings:
            h.weight = round(h.market_value / total_nav * 100, 2) if total_nav > 0 else 0.0

    db.commit()
    return updated


def fetch_benchmark_level(ticker: str) -> float | None:
    return fetch_price(ticker)


def fetch_benchmark_history(ticker: str, period: str = "ytd") -> list[dict]:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period)
        return [
            {"date": idx.strftime("%Y-%m-%d"), "value": float(row["Close"])}
            for idx, row in hist.iterrows()
        ]
    except Exception:
        return []
