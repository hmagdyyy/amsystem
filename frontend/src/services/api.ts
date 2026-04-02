import axios from 'axios';
import type {
  Portfolio,
  PortfolioSummary,
  Holding,
  Order,
  OrderAllocation,
  ComparisonView,
  UploadResult,
  UploadLog,
  CashFlow,
  SectorBreakdown,
} from '../types';

const api = axios.create({
  baseURL: '/api',
});

// Portfolios
export const getPortfolios = () => api.get<Portfolio[]>('/portfolios/');
export const getPortfolio = (id: number) => api.get<Portfolio>(`/portfolios/${id}`);
export const createPortfolio = (data: {
  name: string;
  beginning_nav: number;
  beginning_date: string;
  benchmark_ticker?: string;
  entity_type?: string;
}) => api.post<Portfolio>('/portfolios/', data);
export const createCluster = (data: { name: string; benchmark_ticker?: string }) =>
  api.post<Portfolio>('/portfolios/cluster', data);
export const updatePortfolio = (id: number, data: { name?: string; beginning_nav?: number; benchmark_ticker?: string; beginning_nav_per_unit?: number; entity_type?: string }) =>
  api.put<Portfolio>(`/portfolios/${id}`, data);
export const deletePortfolio = (id: number) => api.delete(`/portfolios/${id}`);
export const getSubPortfolios = (id: number) => api.get<Portfolio[]>(`/portfolios/${id}/sub-portfolios`);
export const getComparisonView = (id: number) => api.get<ComparisonView>(`/portfolios/${id}/comparison`);
export const addMember = (clusterId: number, memberId: number) =>
  api.post<Portfolio>(`/portfolios/${clusterId}/add-member/${memberId}`);
export const removeMember = (memberId: number) =>
  api.post<Portfolio>(`/portfolios/${memberId}/remove-member`);
export const getPortfolioStats = (id: number) =>
  api.get<{ total_return: number; benchmark_return: number | null; equity_exposure: number; funds_exposure: number }>(`/portfolios/${id}/stats`);

// Upload
export const uploadFile = (file: File) => {
  const form = new FormData();
  form.append('file', file);
  return api.post<UploadResult>('/portfolios/upload', form);
};
export const uploadExcel = uploadFile;
export const uploadConsolidated = (clientFilter: File, consolidated: File) => {
  const form = new FormData();
  form.append('client_filter', clientFilter);
  form.append('consolidated', consolidated);
  return api.post<{
    portfolios_updated: number;
    total_holdings: number;
    skipped_sheets: number;
    total_sheets_in_file: number;
    logs: UploadLog[];
  }>('/portfolios/upload-consolidated', form);
};
export const getUploadHistory = () => api.get<UploadLog[]>('/portfolios/uploads/history');

// Holdings
export const getHoldings = (portfolioId: number) =>
  api.get<Holding[]>(`/holdings/portfolio/${portfolioId}`);
export const getSectorBreakdown = (portfolioId: number) =>
  api.get<SectorBreakdown[]>(`/holdings/portfolio/${portfolioId}/sectors`);

// Performance
export const getDashboardSummary = () => api.get<PortfolioSummary[]>('/performance/summary');
export const getNavHistory = (portfolioId: number) =>
  api.get(`/performance/${portfolioId}/nav-history`);
export const getChartData = (portfolioId: number) =>
  api.get<{ portfolio: { date: string; value: number }[]; benchmark: { date: string; value: number }[] }>(
    `/performance/${portfolioId}/chart-data`
  );
export const addCashFlow = (data: {
  portfolio_id: number;
  date: string;
  type: string;
  amount: number;
}) => api.post<CashFlow>('/performance/cash-flow', data);
export const takeSnapshot = (portfolioId: number) =>
  api.post(`/performance/${portfolioId}/snapshot`);

// Orders
export const createOrder = (data: {
  portfolio_id: number;
  ticker: string;
  target_weight: number;
  price: number;
}) => api.post<Order>('/orders/', data);
export const quickOrder = (data: {
  portfolio_id: number;
  ticker: string;
  side: string;
  target_weight: number;
  price?: number;
}) => api.post<Order>('/orders/quick', data);
export const getOrders = (params?: { portfolio_id?: number; status?: string }) =>
  api.get<Order[]>('/orders/', { params });
export const updateOrderStatus = (id: number, status: string) =>
  api.put<Order>(`/orders/${id}/status`, { status });
export const deleteOrder = (id: number) => api.delete(`/orders/${id}`);
export const getOrderAllocations = (orderId: number) =>
  api.get<OrderAllocation[]>(`/orders/${orderId}/allocations`);

// Net Cash Flow
export const getNetCashFlow = (targetDate?: string) =>
  api.get<{
    date: string;
    total_buys: number;
    total_sells: number;
    total_net_cash_flow: number;
    total_net_cash_flow_pct: number;
    portfolios: {
      portfolio_id: number;
      portfolio_name: string;
      current_nav: number;
      buys: number;
      sells: number;
      net_cash_flow: number;
      net_cash_flow_pct: number;
      buy_orders: number;
      sell_orders: number;
      orders: {
        id: number;
        ticker: string;
        side: string;
        shares: number;
        price: number;
        notional: number;
        status: string;
      }[];
    }[];
  }>('/orders/net-cash-flow', { params: targetDate ? { target_date: targetDate } : {} });

// Market Data
export const refreshPrices = (portfolioId: number) =>
  api.post<{ updated: number; portfolio_nav: number }>(`/market-data/refresh/${portfolioId}`);
export const refreshAllPrices = () => api.post<{ total_updated: number }>('/market-data/refresh-all');
export const getPrice = (ticker: string) =>
  api.get<{ ticker: string; price: number }>(`/market-data/price/${ticker}`);
export const getRebalanceView = (portfolioId: number) =>
  api.get(`/market-data/rebalance/${portfolioId}`);

// Export
export const exportHoldingsUrl = (portfolioId: number) =>
  `/api/export/holdings/${portfolioId}`;
export const exportOrdersUrl = (portfolioId?: number) =>
  `/api/export/orders${portfolioId ? `?portfolio_id=${portfolioId}` : ''}`;

export default api;
