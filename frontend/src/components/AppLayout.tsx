import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  FolderOutlined,
  UploadOutlined,
  CalculatorOutlined,
  UnorderedListOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: 'Dashboard' },
  { key: '/portfolios', icon: <FolderOutlined />, label: 'Portfolios' },
  { key: '/upload', icon: <UploadOutlined />, label: 'Upload' },
  { key: '/orders', icon: <CalculatorOutlined />, label: 'Order Builder' },
  { key: '/blotter', icon: <UnorderedListOutlined />, label: 'Order Blotter' },
  { key: '/cash-flow', icon: <DollarOutlined />, label: 'Net Cash Flow' },
];

export default function AppLayout({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={220}
        style={{ background: '#1a1a2e' }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderBottom: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <span style={{ color: '#fff', fontSize: 18, fontWeight: 600, letterSpacing: 1 }}>
            PM System
          </span>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ background: '#1a1a2e', borderRight: 0 }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            borderBottom: '1px solid #e8e8e8',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <span style={{ fontSize: 16, color: '#1a1a2e', fontWeight: 500 }}>
            Portfolio Management
          </span>
        </Header>
        <Content style={{ margin: 24, background: '#f5f5f5', minHeight: 280 }}>
          <div style={{ padding: 24, background: '#fff', borderRadius: 4, minHeight: '100%' }}>
            {children}
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}
