import logging
import openpyxl
from io import BytesIO
from sqlalchemy.orm import Session
from app.models import Portfolio, Holding, UploadLog
from datetime import datetime, date

logger = logging.getLogger(__name__)


def _find_header_row(ws, marker="Stock"):
    """Find the row number where the holdings table header is located."""
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=3):
        for cell in row:
            if cell.value and str(cell.value).strip().lower() == marker.lower():
                return cell.row
    return None


def _get_metadata(ws):
    """Extract portfolio metadata from the sheet."""
    meta = {}
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=3):
        label = row[0].value
        if label is None:
            # Check col B for cover page asset/liability items
            col_b = row[1].value
            if col_b:
                col_b_str = str(col_b).strip()
                col_c = row[2].value
                if col_b_str == "Cash":
                    # Only take the cover page "Cash" line (under Assets), not the detailed cash section
                    if col_c and "cash_balance" not in meta:
                        try:
                            meta["cash_balance"] = float(col_c)
                        except (ValueError, TypeError):
                            pass
                elif col_b_str == "Fees Under Payment":
                    if col_c:
                        try:
                            meta["fees_under_payment"] = float(col_c)
                        except (ValueError, TypeError):
                            pass
                elif col_b_str == "Stock Dividends Receivables":
                    if col_c:
                        try:
                            meta["dividends"] = float(col_c)
                        except (ValueError, TypeError):
                            pass
            continue
        label_str = str(label).strip()
        val = row[1].value
        if label_str == "Client Name":
            meta["client_name"] = str(val).strip() if val else None
        elif label_str == "Currency":
            meta["currency"] = str(val).strip() if val else None
        elif label_str == "Beg. Value":
            meta["beg_value"] = float(val) if val else 0.0
        elif label_str == "Total Capital":
            meta["total_capital"] = float(val) if val else 0.0
        elif label_str == "Activation Date":
            if isinstance(val, datetime):
                meta["activation_date"] = val.date()
            elif isinstance(val, date):
                meta["activation_date"] = val
            elif val:
                val_str = str(val).strip()
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"):
                    try:
                        meta["activation_date"] = datetime.strptime(val_str, fmt).date()
                        break
                    except ValueError:
                        continue
        elif label_str == "Total Net Asset Value After IC Fall":
            meta["nav"] = float(val) if val else 0.0
        elif label_str == "No. Of IC's Outstanding":
            meta["total_units"] = float(val) if val else 0.0
        elif label_str == "IC Price":
            meta["ic_price"] = float(val) if val else 0.0
        elif label_str == "Weighted Return":
            meta["weighted_return"] = float(val) if val else 0.0
        elif label_str == "Absolute Return":
            meta["absolute_return"] = float(val) if val else 0.0

    # Derive beginning NAV per unit from IC price and return
    ic_price = meta.get("ic_price", 0.0)
    ret = meta.get("weighted_return", 0.0)
    if ic_price > 0 and ret != 0:
        meta["beginning_nav_per_unit"] = round(ic_price / (1 + ret / 100), 6)
    elif ic_price > 0:
        meta["beginning_nav_per_unit"] = ic_price

    return meta


def _parse_holdings_section(ws, header_row, holding_type="equity"):
    """Parse holdings from a section starting at header_row.

    The header row has columns like: Sector, Stock, Quantity, Avg. Cost, Price, ...
    Holdings rows have: None in col A (sector col), ticker in col B, data in C onwards.
    Sector header rows have: sector name in col A, None in col B.
    Total rows start with 'Total' in col A.
    """
    holdings = []
    current_sector = None

    # Map header columns by position
    headers = []
    for cell in ws[header_row]:
        headers.append(str(cell.value).strip().lower() if cell.value else "")

    # Find column indices
    col_map = {}
    for i, h in enumerate(headers):
        if h in ("stock", "investment certicate", "investment certificate"):
            col_map["ticker"] = i
        elif h == "quantity":
            col_map["quantity"] = i
        elif h == "avg. cost":
            col_map["avg_cost"] = i
        elif h in ("price", "market price"):
            col_map["price"] = i
        elif h in ("o/s value", "market value"):
            col_map["market_value"] = i
        elif h == "weight":
            col_map["weight"] = i
        elif h in ("unreal. gain/loss",):
            col_map["unrealized"] = i

    if "ticker" not in col_map:
        return holdings, current_sector

    for row in ws.iter_rows(min_row=header_row + 1, max_row=ws.max_row, max_col=len(headers)):
        values = [cell.value for cell in row]

        col_a = values[0]
        col_b = values[col_map["ticker"]] if col_map.get("ticker") is not None else None

        # Empty row
        if all(v is None for v in values):
            continue

        # If col A has a value and col B (ticker) is None, it's a sector header or total row
        if col_a is not None and col_b is None:
            label = str(col_a).strip()
            if label.startswith("Total "):
                continue
            # Check if this is a new section header (like "Investment Certificates", "Call Account")
            # that would indicate end of this holdings section
            if label in ("Investment Certificates", "Call Account", "Prepaid-Amortizing Expenses",
                         "Cash", "Fees", ""):
                break
            current_sector = label
            continue

        # If col A has a value and it starts with "Total" (grand total row), skip
        if col_a is not None:
            label = str(col_a).strip()
            if label.startswith("Total"):
                continue
            # Grand total row (has numbers but col_a is not a sector we recognize)
            # This would be caught by the numeric check below
            if col_b is not None:
                # This might be sector row with a holding in same row - unlikely in this format
                pass

        # If we have a ticker value, parse the holding
        if col_b is not None:
            ticker = str(col_b).strip()
            if not ticker or ticker.lower() == "none":
                continue

            quantity = 0.0
            avg_cost = 0.0
            price = 0.0
            market_value = 0.0
            weight = 0.0

            if "quantity" in col_map and values[col_map["quantity"]] is not None:
                try:
                    quantity = float(values[col_map["quantity"]])
                except (ValueError, TypeError):
                    pass
            if "avg_cost" in col_map and values[col_map["avg_cost"]] is not None:
                try:
                    avg_cost = float(values[col_map["avg_cost"]])
                except (ValueError, TypeError):
                    pass
            if "price" in col_map and values[col_map["price"]] is not None:
                try:
                    price = float(values[col_map["price"]])
                except (ValueError, TypeError):
                    pass
            if "market_value" in col_map and values[col_map["market_value"]] is not None:
                try:
                    market_value = float(values[col_map["market_value"]])
                except (ValueError, TypeError):
                    pass
            if "weight" in col_map and values[col_map["weight"]] is not None:
                try:
                    weight = float(values[col_map["weight"]])
                except (ValueError, TypeError):
                    pass

            holdings.append({
                "ticker": ticker.upper(),
                "sector": current_sector,
                "quantity": quantity,
                "avg_cost": avg_cost,
                "price": price,
                "market_value": market_value,
                "weight": weight,
                "holding_type": holding_type,
            })

    return holdings, current_sector


def parse_client_filter(file_content: bytes) -> set[str]:
    """Parse the client filter Excel to extract allowed sheet names (flat set)."""
    grouped = parse_client_filter_grouped(file_content)
    names = set()
    for group_names in grouped.values():
        names.update(group_names)
    return names


def parse_client_filter_grouped(file_content: bytes) -> dict[str, list[str]]:
    """Parse the client filter Excel and return names grouped by column header.

    Returns e.g. {"Omni": ["Client A", "Client B"], "Separate portfolios": [...], "CFI": [...]}
    """
    wb = openpyxl.load_workbook(BytesIO(file_content), data_only=True)
    groups: dict[str, list[str]] = {}

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        if ws.max_row < 2:
            continue

        # Read header row to identify column groups
        headers: dict[int, str] = {}
        for cell in ws[1]:
            if cell.value and str(cell.value).strip():
                headers[cell.column - 1] = str(cell.value).strip()

        for col_idx, group_name in headers.items():
            if group_name not in groups:
                groups[group_name] = []

        # Read data rows
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=ws.max_column):
            for cell in row:
                col_idx = cell.column - 1
                if col_idx in headers and cell.value and str(cell.value).strip():
                    groups[headers[col_idx]].append(str(cell.value).strip())

    return groups


def _extract_sheet_holdings(ws):
    """Extract metadata and holdings from a single worksheet."""
    meta = _get_metadata(ws)
    all_holdings = []
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=3):
        for cell in row:
            if cell.value and str(cell.value).strip().lower() in ("stock", "investment certicate", "investment certificate"):
                header_row = cell.row
                header_label = str(cell.value).strip().lower()
                h_type = "fund" if header_label in ("investment certicate", "investment certificate") else "equity"
                section_holdings, _ = _parse_holdings_section(ws, header_row, holding_type=h_type)
                all_holdings.extend(section_holdings)
    return meta, all_holdings


def _upsert_portfolio(db: Session, portfolio_name: str, meta: dict, all_holdings: list,
                      parent_id: int | None = None, portfolio_type: str = "standalone") -> Portfolio:
    """Create or update a portfolio with the given holdings."""
    portfolio = db.query(Portfolio).filter(Portfolio.name == portfolio_name).first()

    nav = meta.get("nav", 0.0)
    total_units = meta.get("total_units", 1000.0)
    beg_value = meta.get("beg_value", 0.0)
    activation_date = meta.get("activation_date", datetime.utcnow().date())
    if isinstance(activation_date, datetime):
        activation_date = activation_date.date()
    beg_npu = meta.get("beginning_nav_per_unit", 0.0)

    cash = meta.get("cash_balance", 0.0)
    fees = meta.get("fees_under_payment", 0.0)
    divs = meta.get("dividends", 0.0)

    if not portfolio:
        portfolio = Portfolio(
            name=portfolio_name,
            beginning_nav=beg_value,
            beginning_date=activation_date,
            current_nav=nav if nav else sum(h["market_value"] for h in all_holdings),
            total_units=total_units,
            nav_per_unit=meta.get("ic_price", 0.0),
            beginning_nav_per_unit=beg_npu,
            parent_id=parent_id,
            portfolio_type=portfolio_type,
            cash_balance=cash,
            fees_under_payment=fees,
            dividends=divs,
        )
        db.add(portfolio)
        db.flush()
    else:
        portfolio.current_nav = nav if nav else sum(h["market_value"] for h in all_holdings)
        portfolio.total_units = total_units
        portfolio.nav_per_unit = meta.get("ic_price", 0.0)
        portfolio.parent_id = parent_id
        portfolio.portfolio_type = portfolio_type
        portfolio.cash_balance = cash
        portfolio.fees_under_payment = fees
        portfolio.dividends = divs
        if beg_npu > 0 and portfolio.beginning_nav_per_unit == 0:
            portfolio.beginning_nav_per_unit = beg_npu

    # Clear existing holdings
    db.query(Holding).filter(Holding.portfolio_id == portfolio.id).delete()

    for h in all_holdings:
        ret = ((h["price"] - h["avg_cost"]) / h["avg_cost"] * 100) if h["avg_cost"] > 0 else 0.0
        holding = Holding(
            portfolio_id=portfolio.id,
            ticker=h["ticker"],
            name=None,
            shares=h["quantity"],
            sector=h["sector"],
            cost_per_share=h["avg_cost"],
            market_price=h["price"],
            market_value=h["market_value"],
            weight=round(h["weight"], 2),
            return_pct=round(ret, 2),
            holding_type=h.get("holding_type", "equity"),
        )
        db.add(holding)

    return portfolio


def parse_excel(file_content: bytes, filename: str, db: Session,
                allowed_sheets: set[str] | None = None,
                omni_sheets: set[str] | None = None) -> dict:
    wb = openpyxl.load_workbook(BytesIO(file_content), data_only=True)
    portfolios_updated = 0
    total_holdings = 0
    skipped_sheets = []
    logs = []
    omni_sub_count = 0

    # If there are omni sheets, ensure the parent "Omni" portfolio exists
    omni_parent = None
    if omni_sheets:
        omni_parent = db.query(Portfolio).filter(Portfolio.name == "Omni").first()
        if not omni_parent:
            omni_parent = Portfolio(
                name="Omni",
                beginning_nav=0.0,
                beginning_date=datetime.utcnow().date(),
                current_nav=0.0,
                total_units=1.0,
                nav_per_unit=0.0,
                portfolio_type="parent",
            )
            db.add(omni_parent)
            db.flush()
        else:
            omni_parent.portfolio_type = "parent"

    for sheet_name in wb.sheetnames:
        sn = sheet_name.strip()
        if allowed_sheets is not None and sn not in allowed_sheets:
            skipped_sheets.append(sn)
            continue

        ws = wb[sheet_name]
        meta, all_holdings = _extract_sheet_holdings(ws)

        # Only skip if no holdings AND no NAV metadata (truly empty sheet)
        if not all_holdings and not meta.get("nav"):
            logger.info(f"SKIP sheet '{sn}': no holdings, no NAV metadata")
            continue

        portfolio_name = meta.get("client_name") or sn
        is_omni = omni_sheets is not None and sn in omni_sheets
        logger.info(f"PROCESS sheet '{sn}' -> '{portfolio_name}': NAV={meta.get('nav', 'N/A')}, holdings={len(all_holdings)}, omni={is_omni}")

        if is_omni and omni_parent:
            # Create as sub-portfolio under Omni
            portfolio = _upsert_portfolio(
                db, portfolio_name, meta, all_holdings,
                parent_id=omni_parent.id, portfolio_type="sub",
            )
            omni_sub_count += 1
        else:
            portfolio = _upsert_portfolio(
                db, portfolio_name, meta, all_holdings,
                portfolio_type="standalone",
            )

        holdings_count = len(all_holdings)
        log = UploadLog(
            portfolio_id=portfolio.id,
            filename=filename,
            records_processed=holdings_count,
            status="SUCCESS",
        )
        db.add(log)
        logs.append(log)

        portfolios_updated += 1
        total_holdings += holdings_count

    # Update Omni parent aggregated NAV from sub-portfolios
    if omni_parent:
        subs = db.query(Portfolio).filter(Portfolio.parent_id == omni_parent.id).all()
        for s in sorted(subs, key=lambda x: -x.current_nav):
            logger.info(f"  Omni sub: '{s.name}' NAV={s.current_nav:,.2f}")
        omni_parent.current_nav = sum(s.current_nav for s in subs)
        omni_parent.beginning_nav = sum(s.beginning_nav for s in subs)
        logger.info(f"  Omni TOTAL NAV = {omni_parent.current_nav:,.2f} ({len(subs)} subs)")

        # Aggregate holdings: merge by ticker across all sub-portfolios
        db.query(Holding).filter(Holding.portfolio_id == omni_parent.id).delete()
        sub_ids = [s.id for s in subs]
        if sub_ids:
            all_sub_holdings = db.query(Holding).filter(Holding.portfolio_id.in_(sub_ids)).all()
            merged: dict[str, dict] = {}
            for h in all_sub_holdings:
                key = (h.ticker, h.holding_type)
                if key not in merged:
                    merged[key] = {
                        "ticker": h.ticker,
                        "sector": h.sector,
                        "shares": 0.0,
                        "total_cost": 0.0,
                        "market_value": 0.0,
                        "holding_type": h.holding_type,
                        "market_price": h.market_price,
                    }
                merged[key]["shares"] += h.shares
                merged[key]["total_cost"] += h.shares * h.cost_per_share
                merged[key]["market_value"] += h.market_value

            for m in merged.values():
                avg_cost = m["total_cost"] / m["shares"] if m["shares"] > 0 else 0.0
                ret = ((m["market_price"] - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0.0
                weight = (m["market_value"] / omni_parent.current_nav * 100) if omni_parent.current_nav > 0 else 0.0
                holding = Holding(
                    portfolio_id=omni_parent.id,
                    ticker=m["ticker"],
                    name=None,
                    shares=m["shares"],
                    sector=m["sector"],
                    cost_per_share=round(avg_cost, 4),
                    market_price=m["market_price"],
                    market_value=m["market_value"],
                    weight=round(weight, 2),
                    return_pct=round(ret, 2),
                    holding_type=m["holding_type"],
                )
                db.add(holding)

    db.commit()

    return {
        "portfolios_updated": portfolios_updated,
        "total_holdings": total_holdings,
        "logs": logs,
        "skipped_sheets": skipped_sheets,
        "omni_sub_portfolios": omni_sub_count,
    }
