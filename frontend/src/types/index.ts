export interface Portfolio {
  id: number;
  name: string;
  beginning_nav: number;
  beginning_date: string;
  current_nav: number;
  total_units: number;
  nav_per_unit: number;
  beginning_nav_per_unit: number;
  benchmark_ticker: string | null;
  parent_id: number | null;
  portfolio_type: string;
  entity_type: string;
  created_at: string;
  updated_at: string;
}

export interface OrderAllocation {
  sub_portfolio_id: number;
  sub_portfolio_name: string;
  nav: number;
  nav_weight_pct: number;
  allocated_shares: number;
  notional: number;
}

export interface ComparisonRow {
  sub_portfolio_id: number;
  client: string;
  cash: number;
  fees_under_payment: number;
  dividends: number;
  funds: Record<string, number>;
  total_cash: number;
  stocks: Record<string, number>;
  nav: number;
}

export interface ComparisonView {
  fund_tickers: string[];
  equity_tickers: string[];
  rows: ComparisonRow[];
  total_nav: number;
}

export interface PortfolioSummary {
  id: number;
  name: string;
  beginning_nav: number;
  current_nav: number;
  nav_per_unit: number;
  entity_type: string;
  ytd_return: number;
  nav_return: number | null;
  equity_exposure: number;
  benchmark_return: number | null;
  alpha: number | null;
  benchmark_ticker: string | null;
  portfolio_type: string;
  children: PortfolioSummary[];
}

export interface Holding {
  id: number;
  portfolio_id: number;
  ticker: string;
  name: string | null;
  shares: number;
  cost_per_share: number;
  market_price: number;
  market_value: number;
  weight: number;
  return_pct: number;
  sector: string | null;
  updated_at: string;
}

export interface CashFlow {
  id: number;
  portfolio_id: number;
  date: string;
  type: string;
  amount: number;
  units_changed: number;
  nav_per_unit_at_flow: number;
}

export interface Order {
  id: number;
  portfolio_id: number;
  ticker: string;
  side: string;
  target_weight: number;
  current_weight: number;
  shares: number;
  price: number;
  notional_amount: number;
  status: string;
  bloomberg_message: string | null;
  created_at: string;
  updated_at: string;
  portfolio_name: string | null;
}

export interface NavHistoryPoint {
  date: string;
  value: number;
}

export interface UploadLog {
  id: number;
  portfolio_id: number | null;
  filename: string;
  uploaded_at: string;
  records_processed: number;
  status: string;
}

export interface UploadResult {
  portfolios_updated: number;
  total_holdings: number;
  logs: UploadLog[];
}

export interface SectorBreakdown {
  sector: string;
  weight: number;
}
