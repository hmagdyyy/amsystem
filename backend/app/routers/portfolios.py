from datetime import date

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.config import get_db
from app.models import Portfolio, UploadLog
from app.schemas.portfolio import PortfolioCreate, ClusterCreate, PortfolioUpdate, PortfolioResponse
from app.schemas.upload import UploadLogResponse, UploadResult
from app.services.excel_parser import parse_excel, parse_client_filter, parse_client_filter_grouped
from app.services.pdf_parser import parse_pdf
from app.services.ic_engine import calculate_ytd_return
from app.services.benchmark import get_benchmark_ytd_return

router = APIRouter(prefix="/api/portfolios", tags=["portfolios"])


@router.get("/", response_model=list[PortfolioResponse])
def list_portfolios(db: Session = Depends(get_db)):
    return db.query(Portfolio).order_by(Portfolio.name).all()


@router.post("/", response_model=PortfolioResponse)
def create_portfolio(data: PortfolioCreate, db: Session = Depends(get_db)):
    existing = db.query(Portfolio).filter(Portfolio.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Portfolio name already exists")

    nav_per_unit = data.beginning_nav / 1000.0 if data.beginning_nav > 0 else 0.0
    portfolio = Portfolio(
        name=data.name,
        beginning_nav=data.beginning_nav,
        beginning_date=data.beginning_date,
        current_nav=data.beginning_nav,
        total_units=1000.0,
        nav_per_unit=nav_per_unit,
        benchmark_ticker=data.benchmark_ticker,
        entity_type=data.entity_type,
        portfolio_type="standalone",
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


@router.post("/cluster", response_model=PortfolioResponse)
def create_cluster(data: ClusterCreate, db: Session = Depends(get_db)):
    """Create a cluster (parent) portfolio — a lightweight container that groups other portfolios."""
    existing = db.query(Portfolio).filter(Portfolio.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Portfolio name already exists")

    cluster = Portfolio(
        name=data.name,
        beginning_nav=0.0,
        beginning_date=date.today(),
        current_nav=0.0,
        total_units=0.0,
        nav_per_unit=0.0,
        benchmark_ticker=data.benchmark_ticker,
        entity_type="fund",
        portfolio_type="parent",
    )
    db.add(cluster)
    db.commit()
    db.refresh(cluster)
    return cluster


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
def get_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@router.get("/{portfolio_id}/sub-portfolios", response_model=list[PortfolioResponse])
def get_sub_portfolios(portfolio_id: int, db: Session = Depends(get_db)):
    """Get all member portfolios for a cluster."""
    return db.query(Portfolio).filter(Portfolio.parent_id == portfolio_id).order_by(Portfolio.name).all()


@router.get("/{portfolio_id}/comparison")
def get_comparison_view(portfolio_id: int, db: Session = Depends(get_db)):
    """Get Omni-style comparison view: per-client breakdown of cash, funds, stock qtys, NAV."""
    from app.models import Holding

    parent = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not parent or parent.portfolio_type != "parent":
        raise HTTPException(status_code=400, detail="Comparison view only available for parent portfolios")

    subs = db.query(Portfolio).filter(Portfolio.parent_id == parent.id).all()

    # Collect all unique equity tickers and fund tickers across all sub-portfolios
    sub_ids = [s.id for s in subs]
    all_holdings = db.query(Holding).filter(Holding.portfolio_id.in_(sub_ids)).all() if sub_ids else []

    equity_tickers = sorted({h.ticker for h in all_holdings if h.holding_type == "equity"})
    fund_tickers = sorted({h.ticker for h in all_holdings if h.holding_type == "fund"})

    # Build per-sub-portfolio lookup: {portfolio_id: {ticker: holding}}
    holdings_map: dict[int, dict[str, "Holding"]] = {}
    for h in all_holdings:
        holdings_map.setdefault(h.portfolio_id, {})[h.ticker] = h

    rows = []
    for sub in sorted(subs, key=lambda s: s.current_nav, reverse=True):
        sub_holdings = holdings_map.get(sub.id, {})

        # Fund values (market_value)
        funds = {}
        for ft in fund_tickers:
            h = sub_holdings.get(ft)
            funds[ft] = h.market_value if h else 0.0

        # Stock quantities
        stocks = {}
        for et in equity_tickers:
            h = sub_holdings.get(et)
            stocks[et] = h.shares if h else 0.0

        # Total cash = cash_balance - fees + dividends + fund values
        total_cash = sub.cash_balance + sum(funds.values())

        rows.append({
            "sub_portfolio_id": sub.id,
            "client": sub.name,
            "cash": round(sub.cash_balance, 2),
            "fees_under_payment": round(sub.fees_under_payment, 2),
            "dividends": round(sub.dividends, 2),
            "funds": {k: round(v, 2) for k, v in funds.items()},
            "total_cash": round(total_cash, 2),
            "stocks": stocks,
            "nav": round(sub.current_nav, 2),
        })

    return {
        "fund_tickers": fund_tickers,
        "equity_tickers": equity_tickers,
        "rows": rows,
        "total_nav": round(sum(r["nav"] for r in rows), 2),
    }


@router.put("/{portfolio_id}", response_model=PortfolioResponse)
def update_portfolio(portfolio_id: int, data: PortfolioUpdate, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if data.name is not None:
        portfolio.name = data.name
    if data.beginning_nav is not None:
        portfolio.beginning_nav = data.beginning_nav
    if data.beginning_nav_per_unit is not None:
        portfolio.beginning_nav_per_unit = data.beginning_nav_per_unit
    if data.benchmark_ticker is not None:
        portfolio.benchmark_ticker = data.benchmark_ticker
    if data.entity_type is not None:
        portfolio.entity_type = data.entity_type
    db.commit()
    db.refresh(portfolio)
    return portfolio


@router.post("/{portfolio_id}/add-member/{member_id}", response_model=PortfolioResponse)
def add_member(portfolio_id: int, member_id: int, db: Session = Depends(get_db)):
    """Add an existing portfolio as a member of a cluster."""
    cluster = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    if cluster.portfolio_type != "parent":
        raise HTTPException(status_code=400, detail="Can only add members to a cluster")

    member = db.query(Portfolio).filter(Portfolio.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if member.portfolio_type == "parent":
        raise HTTPException(status_code=400, detail="Cannot add a cluster as a member of another cluster")
    if member.parent_id is not None:
        raise HTTPException(status_code=400, detail="Portfolio already belongs to a cluster")
    if portfolio_id == member_id:
        raise HTTPException(status_code=400, detail="Cannot add a cluster to itself")

    member.parent_id = cluster.id
    # Don't change member's portfolio_type — it stays standalone

    # Update cluster's aggregated NAV
    cluster.current_nav = sum(
        p.current_nav for p in db.query(Portfolio).filter(Portfolio.parent_id == cluster.id).all()
    ) + member.current_nav

    db.commit()
    db.refresh(member)
    return member


@router.post("/{portfolio_id}/remove-member", response_model=PortfolioResponse)
def remove_member(portfolio_id: int, db: Session = Depends(get_db)):
    """Remove a portfolio from its cluster."""
    member = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if member.parent_id is None:
        raise HTTPException(status_code=400, detail="Portfolio is not in a cluster")

    old_parent_id = member.parent_id
    member.parent_id = None

    # Update cluster's aggregated NAV
    cluster = db.query(Portfolio).filter(Portfolio.id == old_parent_id).first()
    if cluster:
        cluster.current_nav = sum(
            p.current_nav for p in db.query(Portfolio).filter(
                Portfolio.parent_id == old_parent_id, Portfolio.id != portfolio_id
            ).all()
        )

    db.commit()
    db.refresh(member)
    return member


@router.delete("/{portfolio_id}")
def delete_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # If deleting a cluster, unlink all members first
    if portfolio.portfolio_type == "parent":
        db.query(Portfolio).filter(Portfolio.parent_id == portfolio_id).update({"parent_id": None})

    db.delete(portfolio)
    db.commit()
    return {"detail": "Deleted"}


@router.get("/{portfolio_id}/stats")
def get_portfolio_stats(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    from app.models import Holding

    # For clusters, aggregate holdings from all members
    if portfolio.portfolio_type == "parent":
        member_ids = [
            c.id for c in db.query(Portfolio.id).filter(Portfolio.parent_id == portfolio_id).all()
        ]
        holdings = db.query(Holding).filter(Holding.portfolio_id.in_(member_ids)).all() if member_ids else []
        total_nav = sum(
            p.current_nav for p in db.query(Portfolio).filter(Portfolio.parent_id == portfolio_id).all()
        )
    else:
        holdings = db.query(Holding).filter(Holding.portfolio_id == portfolio_id).all()
        total_nav = portfolio.current_nav

    # Total return (IC price based)
    total_return = calculate_ytd_return(db, portfolio_id)

    # Benchmark return
    benchmark_return = None
    if portfolio.benchmark_ticker:
        benchmark_return = get_benchmark_ytd_return(portfolio.benchmark_ticker)

    # Equity exposure = sum of equity holdings market values / NAV
    equity_value = sum(h.market_value for h in holdings if h.holding_type == "equity")
    equity_exposure = round(equity_value / total_nav * 100, 2) if total_nav > 0 else 0.0

    # Funds exposure = sum of fund holdings market values / NAV
    funds_value = sum(h.market_value for h in holdings if h.holding_type == "fund")
    funds_exposure = round(funds_value / total_nav * 100, 2) if total_nav > 0 else 0.0

    return {
        "total_return": total_return,
        "benchmark_return": benchmark_return,
        "equity_exposure": equity_exposure,
        "funds_exposure": funds_exposure,
    }


@router.post("/upload", response_model=UploadResult)
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.endswith((".xlsx", ".xls", ".pdf")):
        raise HTTPException(status_code=400, detail="Only Excel (.xlsx, .xls) and PDF (.pdf) files are supported")

    content = await file.read()
    try:
        if file.filename.lower().endswith(".pdf"):
            result = parse_pdf(content, file.filename, db)
        else:
            result = parse_excel(content, file.filename, db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing file: {str(e)}")

    return UploadResult(
        portfolios_updated=result["portfolios_updated"],
        total_holdings=result["total_holdings"],
        logs=[UploadLogResponse.model_validate(log) for log in result["logs"]],
    )


@router.post("/upload-consolidated")
async def upload_consolidated(
    client_filter: UploadFile = File(...),
    consolidated: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a consolidated Excel with all portfolios, filtered by a client list file.

    Sheets under the 'Omni' column become sub-portfolios of a parent 'Omni' portfolio.
    Sheets under other columns become standalone portfolios.
    """
    if not client_filter.filename or not client_filter.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Client filter must be an Excel file")
    if not consolidated.filename or not consolidated.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Consolidated file must be an Excel file")

    filter_content = await client_filter.read()
    consolidated_content = await consolidated.read()

    try:
        groups = parse_client_filter_grouped(filter_content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing client filter: {str(e)}")

    # Build allowed_sheets and identify Omni sheets
    all_allowed = set()
    omni_sheets = set()
    for group_name, names in groups.items():
        all_allowed.update(names)
        if group_name.lower() == "omni":
            omni_sheets.update(names)

    try:
        result = parse_excel(
            consolidated_content, consolidated.filename, db,
            allowed_sheets=all_allowed,
            omni_sheets=omni_sheets,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing consolidated file: {str(e)}")

    return {
        "portfolios_updated": result["portfolios_updated"],
        "total_holdings": result["total_holdings"],
        "skipped_sheets": len(result.get("skipped_sheets", [])),
        "total_sheets_in_file": result["portfolios_updated"] + len(result.get("skipped_sheets", [])),
        "omni_sub_portfolios": result.get("omni_sub_portfolios", 0),
        "logs": [UploadLogResponse.model_validate(log) for log in result["logs"]],
    }


@router.get("/uploads/history", response_model=list[UploadLogResponse])
def upload_history(db: Session = Depends(get_db)):
    return db.query(UploadLog).order_by(UploadLog.uploaded_at.desc()).limit(50).all()
