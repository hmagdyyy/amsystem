import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import AppLayout from './components/AppLayout';
import Dashboard from './pages/Dashboard';
import Portfolios from './pages/Portfolios';
import PortfolioDetail from './pages/PortfolioDetail';
import Upload from './pages/Upload';
import OrderBuilder from './pages/OrderBuilder';
import OrderBlotter from './pages/OrderBlotter';
import NetCashFlow from './pages/NetCashFlow';

const neutralTheme = {
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: '#1a1a2e',
    colorSuccess: '#1a1a2e',
    colorWarning: '#1a1a2e',
    colorError: '#1a1a2e',
    colorInfo: '#1a1a2e',
    borderRadius: 4,
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  },
};

function App() {
  return (
    <ConfigProvider theme={neutralTheme}>
      <BrowserRouter>
        <AppLayout>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/portfolios" element={<Portfolios />} />
            <Route path="/portfolios/:id" element={<PortfolioDetail />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/orders" element={<OrderBuilder />} />
            <Route path="/blotter" element={<OrderBlotter />} />
            <Route path="/cash-flow" element={<NetCashFlow />} />
          </Routes>
        </AppLayout>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
