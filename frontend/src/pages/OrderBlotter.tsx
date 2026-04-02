import { useEffect, useState } from 'react';
import { Table, Select, Space, Button, message, Modal } from 'antd';
import { DownloadOutlined, TeamOutlined } from '@ant-design/icons';
import { getOrders, getPortfolios, updateOrderStatus, deleteOrder, exportOrdersUrl, getOrderAllocations } from '../services/api';
import type { Order, Portfolio, OrderAllocation } from '../types';

export default function OrderBlotter() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterPortfolio, setFilterPortfolio] = useState<number | undefined>();
  const [filterStatus, setFilterStatus] = useState<string | undefined>();
  const [allocations, setAllocations] = useState<OrderAllocation[]>([]);
  const [allocModalOpen, setAllocModalOpen] = useState(false);
  const [allocOrder, setAllocOrder] = useState<Order | null>(null);

  useEffect(() => {
    loadPortfolios();
  }, []);

  useEffect(() => {
    loadOrders();
  }, [filterPortfolio, filterStatus]);

  const loadPortfolios = async () => {
    try {
      const res = await getPortfolios();
      setPortfolios(res.data);
    } catch {
      // ignore
    }
  };

  const loadOrders = async () => {
    setLoading(true);
    try {
      const res = await getOrders({
        portfolio_id: filterPortfolio,
        status: filterStatus,
      });
      setOrders(res.data);
    } catch {
      message.error('Failed to load orders');
    }
    setLoading(false);
  };

  const handleStatusChange = async (orderId: number, status: string) => {
    try {
      await updateOrderStatus(orderId, status);
      loadOrders();
    } catch {
      message.error('Failed to update status');
    }
  };

  const handleDelete = async (orderId: number) => {
    await deleteOrder(orderId);
    loadOrders();
  };

  const copyBloomberg = (msg: string) => {
    navigator.clipboard.writeText(msg);
    message.success('Copied');
  };

  const showAllocations = async (order: Order) => {
    try {
      const res = await getOrderAllocations(order.id);
      setAllocations(res.data);
      setAllocOrder(order);
      setAllocModalOpen(true);
    } catch {
      message.error('Failed to load allocations');
    }
  };

  // Check if a portfolio is a parent type
  const isParentPortfolio = (portfolioId: number) => {
    const p = portfolios.find(pp => pp.id === portfolioId);
    return p?.portfolio_type === 'parent';
  };

  const allocationColumns = [
    { title: 'Client', dataIndex: 'sub_portfolio_name', key: 'name' },
    {
      title: 'NAV',
      dataIndex: 'nav',
      key: 'nav',
      render: (v: number) => v.toLocaleString('en-US', { maximumFractionDigits: 0 }),
    },
    { title: 'Weight', dataIndex: 'nav_weight_pct', key: 'weight', render: (v: number) => `${v.toFixed(2)}%` },
    { title: 'Shares', dataIndex: 'allocated_shares', key: 'shares', render: (v: number) => v.toLocaleString() },
    {
      title: 'Notional',
      dataIndex: 'notional',
      key: 'notional',
      render: (v: number) => v.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }),
    },
  ];

  const columns = [
    { title: 'Portfolio', dataIndex: 'portfolio_name', key: 'portfolio_name' },
    { title: 'Ticker', dataIndex: 'ticker', key: 'ticker' },
    { title: 'Side', dataIndex: 'side', key: 'side' },
    { title: 'Shares', dataIndex: 'shares', key: 'shares', render: (v: number) => v.toLocaleString() },
    { title: 'Price', dataIndex: 'price', key: 'price', render: (v: number) => `$${v.toFixed(2)}` },
    {
      title: 'Notional',
      dataIndex: 'notional_amount',
      key: 'notional_amount',
      render: (v: number) => v.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }),
    },
    { title: 'Target %', dataIndex: 'target_weight', key: 'target_weight', render: (v: number) => `${v}%` },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string, record: Order) => (
        <Select
          value={status}
          size="small"
          style={{ width: 110 }}
          onChange={(val) => handleStatusChange(record.id, val)}
          options={[
            { label: 'Draft', value: 'DRAFT' },
            { label: 'Pending', value: 'PENDING' },
            { label: 'Sent', value: 'SENT' },
            { label: 'Filled', value: 'FILLED' },
            { label: 'Cancelled', value: 'CANCELLED' },
          ]}
        />
      ),
    },
    {
      title: 'Bloomberg',
      key: 'bloomberg',
      render: (_: unknown, record: Order) =>
        record.bloomberg_message ? (
          <Button type="link" size="small" onClick={() => copyBloomberg(record.bloomberg_message!)} style={{ color: '#1a1a2e', padding: 0 }}>
            Copy
          </Button>
        ) : null,
    },
    {
      title: '',
      key: 'actions',
      render: (_: unknown, record: Order) => (
        <Space>
          {isParentPortfolio(record.portfolio_id) && (
            <Button type="link" size="small" icon={<TeamOutlined />} onClick={() => showAllocations(record)} style={{ color: '#1a1a2e', padding: 0 }}>
              Allocations
            </Button>
          )}
          <Button type="link" size="small" onClick={() => handleDelete(record.id)} style={{ color: '#666' }}>
            Delete
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0, color: '#1a1a2e' }}>Order Blotter</h2>
        <Button icon={<DownloadOutlined />} href={exportOrdersUrl(filterPortfolio)}>
          Export CSV
        </Button>
      </div>

      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="All Portfolios"
          allowClear
          style={{ width: 200 }}
          onChange={setFilterPortfolio}
          options={portfolios.map((p) => ({ label: p.name, value: p.id }))}
        />
        <Select
          placeholder="All Statuses"
          allowClear
          style={{ width: 140 }}
          onChange={setFilterStatus}
          options={[
            { label: 'Draft', value: 'DRAFT' },
            { label: 'Pending', value: 'PENDING' },
            { label: 'Sent', value: 'SENT' },
            { label: 'Filled', value: 'FILLED' },
            { label: 'Cancelled', value: 'CANCELLED' },
          ]}
        />
      </Space>

      <Table
        dataSource={orders}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 25 }}
        size="small"
      />

      <Modal
        title={allocOrder ? `Order Allocations — ${allocOrder.side} ${allocOrder.shares.toLocaleString()} ${allocOrder.ticker}` : 'Allocations'}
        open={allocModalOpen}
        onCancel={() => setAllocModalOpen(false)}
        footer={null}
        width={700}
      >
        <Table
          dataSource={allocations}
          columns={allocationColumns}
          rowKey="sub_portfolio_id"
          pagination={false}
          size="small"
          summary={() =>
            allocations.length > 0 ? (
              <Table.Summary.Row>
                <Table.Summary.Cell index={0}><strong>Total</strong></Table.Summary.Cell>
                <Table.Summary.Cell index={1} />
                <Table.Summary.Cell index={2}><strong>100%</strong></Table.Summary.Cell>
                <Table.Summary.Cell index={3}>
                  <strong>{allocations.reduce((s, a) => s + a.allocated_shares, 0).toLocaleString()}</strong>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={4}>
                  <strong>{allocations.reduce((s, a) => s + a.notional, 0).toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })}</strong>
                </Table.Summary.Cell>
              </Table.Summary.Row>
            ) : null
          }
        />
      </Modal>
    </div>
  );
}
