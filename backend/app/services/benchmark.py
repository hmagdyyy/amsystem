from datetime import date
from app.services.market_data import fetch_benchmark_history


def get_benchmark_ytd_return(ticker: str) -> float | None:
    if not ticker:
        return None
    try:
        history = fetch_benchmark_history(ticker, period="ytd")
        if len(history) < 2:
            return None
        start_value = history[0]["value"]
        end_value = history[-1]["value"]
        if start_value > 0:
            return round((end_value / start_value - 1) * 100, 2)
    except Exception:
        pass
    return None


def get_benchmark_series(ticker: str, period: str = "ytd") -> list[dict]:
    if not ticker:
        return []
    history = fetch_benchmark_history(ticker, period)
    if not history:
        return []
    base = history[0]["value"]
    if base <= 0:
        return []
    return [
        {"date": h["date"], "value": round(h["value"] / base * 100, 2)}
        for h in history
    ]
