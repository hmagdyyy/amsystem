import fitz  # PyMuPDF
from io import BytesIO
from sqlalchemy.orm import Session
from app.models import Portfolio, Holding, UploadLog
from datetime import datetime, date
import re


def _parse_number(s: str) -> float:
    """Parse a number string like '1,045,000.00' or '0.84 %' into a float."""
    if s is None:
        return 0.0
    s = str(s).strip().replace('%', '').replace(',', '').strip()
    if not s:
        return 0.0
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def _extract_metadata(pages_text: list[str]) -> dict:
    """Extract portfolio metadata from all pages.

    Uses a multi-pass approach:
    1. First pass on page 1: get fund name and Total Asset Value
    2. Last page summary: get IC Price, No. of ICs Outstanding, Net Asset Value
    3. Page 2 area: get Beg. Date, Init. Value, Total Capital
    """
    meta = {}
    all_text = "\n".join(pages_text)
    all_lines = all_text.split('\n')

    # --- Fund name: look for a line containing "Fund" and a recognizable keyword ---
    for line in all_lines:
        line_s = line.strip()
        if len(line_s) > 10 and 'Fund' in line_s and line_s not in ('Fund Currency:',):
            meta["client_name"] = line_s.rstrip('-').strip()
            break

    # --- Last page summary section (most reliable for IC Price, units, NAV) ---
    if pages_text:
        last_page_lines = pages_text[-1].split('\n')
        for i, line in enumerate(last_page_lines):
            line_s = line.strip()

            # "IC Price :" followed by units count then IC price value
            if line_s.startswith('IC Price') and ':' in line_s:
                # Next lines: units count, then IC price
                nums = []
                for j in range(i + 1, min(i + 5, len(last_page_lines))):
                    v = _parse_number(last_page_lines[j].strip())
                    if v > 0:
                        nums.append(v)
                    elif last_page_lines[j].strip() and not re.match(r'^[\d,.\s%]+$', last_page_lines[j].strip()):
                        break
                if len(nums) >= 2:
                    # The larger number is units, the smaller is IC price
                    meta["total_units"] = max(nums[0], nums[1])
                    meta["ic_price"] = min(nums[0], nums[1])
                elif len(nums) == 1:
                    meta["ic_price"] = nums[0]

            # "Net Asset Value :" or "Net Market Value :"
            if 'Net Asset Value :' in line_s or 'Net Market Value :' in line_s:
                # The NAV value is typically on a preceding line (PDF layout quirk)
                pass

    # --- Page 1: Total Asset Value and NAV ---
    if pages_text:
        p1_lines = pages_text[0].split('\n')
        for i, line in enumerate(p1_lines):
            line_s = line.strip()

            if 'Total  Asset Value' in line_s or 'Total Asset Value' in line_s:
                # Value is on the preceding line
                if i > 0:
                    val = _parse_number(p1_lines[i - 1].strip())
                    if val > 0:
                        meta["nav"] = val

            if line_s == 'IC Price Fall' or 'Total Net Asset Value' in line_s:
                # Look backwards for the NAV value
                for j in range(i - 1, max(i - 5, -1), -1):
                    val = _parse_number(p1_lines[j].strip())
                    if val > 1000:
                        if "nav" not in meta:
                            meta["nav"] = val
                        break

    # --- Dates and initial values from page 2 text ---
    for line in all_lines:
        line_s = line.strip()

        # Beg. Date
        if 'activation_date' not in meta:
            for fmt_label in ('Beg. Date:', 'Activation Date'):
                if fmt_label in line_s:
                    # Look for date pattern in nearby lines
                    idx = all_lines.index(line)
                    for j in range(idx - 2, min(idx + 5, len(all_lines))):
                        if j < 0:
                            continue
                        val = all_lines[j].strip()
                        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
                            try:
                                meta["activation_date"] = datetime.strptime(val, fmt).date()
                                break
                            except ValueError:
                                continue
                        if "activation_date" in meta:
                            break

        # Total Capital
        if 'total_capital' not in meta and 'Total Capital:' in line_s:
            idx = all_lines.index(line)
            for j in range(idx + 1, min(idx + 5, len(all_lines))):
                val = _parse_number(all_lines[j].strip())
                if val > 0:
                    meta["total_capital"] = val
                    break

        # Init. Value / Beg. Value
        if 'beg_value' not in meta and ('Init. Value:' in line_s or 'Beg. Value' in line_s):
            idx = all_lines.index(line)
            for j in range(idx + 1, min(idx + 5, len(all_lines))):
                val = _parse_number(all_lines[j].strip())
                if val > 0:
                    meta["beg_value"] = val
                    break

    return meta


def _parse_stock_table(table_data: list) -> list:
    """Parse a stock table extracted by PyMuPDF."""
    if not table_data or len(table_data) < 2:
        return []

    header = table_data[0]
    holdings = []

    # Find column indices from header
    col_map = {}
    for i, h in enumerate(header):
        if h is None:
            continue
        h_lower = h.strip().lower()
        if h_lower in ('stock', 'investment certificate'):
            col_map['ticker'] = i
        elif h_lower == 'quantity':
            col_map['quantity'] = i
        elif h_lower in ('m.price', 'm. price', 'market price', 'price'):
            col_map['price'] = i
        elif h_lower in ('market value',) and 'market_value' not in col_map:
            col_map['market_value'] = i
        elif h_lower == 'weight':
            col_map['weight'] = i
        elif h_lower in ('markect value', 'markect value'):
            # Typo in PDF for "Market Value" - this is actually the cost/initial value
            if 'market_value_initial' not in col_map:
                col_map['market_value_initial'] = i

    if 'ticker' not in col_map:
        return []

    # In the PDF tables, data is newline-separated within cells
    # Each cell contains all rows for that column joined by \n
    data_row = table_data[1]

    # Get the stock names
    ticker_col = col_map['ticker']
    if ticker_col >= len(data_row) or data_row[ticker_col] is None:
        return []

    stock_names = data_row[ticker_col].split('\n')

    # Get quantities
    quantities = []
    if 'quantity' in col_map and col_map['quantity'] < len(data_row) and data_row[col_map['quantity']]:
        quantities = data_row[col_map['quantity']].split('\n')

    # Get prices
    prices = []
    if 'price' in col_map and col_map['price'] < len(data_row) and data_row[col_map['price']]:
        prices = data_row[col_map['price']].split('\n')

    # Get market values - use the last "Market Value" column (which is the actual market value)
    market_values = []
    if 'market_value' in col_map and col_map['market_value'] < len(data_row) and data_row[col_map['market_value']]:
        market_values = data_row[col_map['market_value']].split('\n')

    # Get weights
    weights = []
    if 'weight' in col_map and col_map['weight'] < len(data_row) and data_row[col_map['weight']]:
        weights = data_row[col_map['weight']].split('\n')

    for idx, name in enumerate(stock_names):
        name = name.strip()
        if not name or name.lower() == 'none':
            continue

        quantity = _parse_number(quantities[idx]) if idx < len(quantities) else 0.0
        price = _parse_number(prices[idx]) if idx < len(prices) else 0.0
        market_value = _parse_number(market_values[idx]) if idx < len(market_values) else 0.0
        weight = _parse_number(weights[idx]) if idx < len(weights) else 0.0

        holdings.append({
            "ticker": name.upper(),
            "sector": None,
            "quantity": quantity,
            "avg_cost": 0.0,  # PDF doesn't have avg cost
            "price": price,
            "market_value": market_value,
            "weight": weight,
        })

    return holdings


def parse_pdf(file_content: bytes, filename: str, db: Session) -> dict:
    """Parse a PDF portfolio statement and store in database."""
    doc = fitz.open(stream=file_content, filetype="pdf")

    # Extract per-page text for metadata
    pages_text = [page.get_text() for page in doc]
    meta = _extract_metadata(pages_text)

    # Extract tables from all pages
    all_holdings = []
    for page in doc:
        tabs = page.find_tables()
        for tab in tabs:
            table_data = tab.extract()
            if not table_data:
                continue

            header = table_data[0]
            if header is None:
                continue

            # Check if this is a stock or investment certificate table
            header_lower = [str(h).lower() if h else '' for h in header]
            is_holdings_table = any(
                h in ('stock', 'investment certificate')
                for h in header_lower
            )

            if is_holdings_table:
                holdings = _parse_stock_table(table_data)
                all_holdings.extend(holdings)

    doc.close()

    if not all_holdings:
        return {"portfolios_updated": 0, "total_holdings": 0, "logs": []}

    # Determine portfolio name
    portfolio_name = meta.get("client_name", filename.replace(".pdf", "").strip())

    nav = meta.get("nav", 0.0)
    total_units = meta.get("total_units", 1000.0)
    beg_value = meta.get("beg_value", 0.0)
    activation_date = meta.get("activation_date", datetime.utcnow().date())
    if isinstance(activation_date, datetime):
        activation_date = activation_date.date()

    # Create or update portfolio
    portfolio = db.query(Portfolio).filter(Portfolio.name == portfolio_name).first()

    if not portfolio:
        portfolio = Portfolio(
            name=portfolio_name,
            beginning_nav=beg_value,
            beginning_date=activation_date,
            current_nav=nav if nav else sum(h["market_value"] for h in all_holdings),
            total_units=total_units,
            nav_per_unit=meta.get("ic_price", 0.0),
        )
        db.add(portfolio)
        db.flush()
    else:
        portfolio.current_nav = nav if nav else sum(h["market_value"] for h in all_holdings)
        portfolio.total_units = total_units
        portfolio.nav_per_unit = meta.get("ic_price", 0.0)

    # Clear existing holdings
    db.query(Holding).filter(Holding.portfolio_id == portfolio.id).delete()

    nav_total = sum(h["market_value"] for h in all_holdings)

    for h in all_holdings:
        ret = ((h["price"] - h["avg_cost"]) / h["avg_cost"] * 100) if h["avg_cost"] > 0 else 0.0
        weight = (h["market_value"] / nav_total * 100) if nav_total > 0 else 0.0

        holding = Holding(
            portfolio_id=portfolio.id,
            ticker=h["ticker"],
            name=None,
            sector=h.get("sector"),
            shares=h["quantity"],
            cost_per_share=h["avg_cost"],
            market_price=h["price"],
            market_value=h["market_value"],
            weight=round(weight, 2),
            return_pct=round(ret, 2),
        )
        db.add(holding)

    holdings_count = len(all_holdings)

    log = UploadLog(
        portfolio_id=portfolio.id,
        filename=filename,
        records_processed=holdings_count,
        status="SUCCESS",
    )
    db.add(log)

    db.commit()

    return {
        "portfolios_updated": 1,
        "total_holdings": holdings_count,
        "logs": [log],
    }
