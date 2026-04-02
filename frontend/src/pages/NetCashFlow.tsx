import { useEffect, useState } from 'react';
import { Card, Table, Row, Col, DatePicker, Tag, Space } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { getNetCashFlow } from '../services/api';

interface OrderDetail {
  id: number;
  ticker: string;
  side: string;
  shares: number;
  price: number;
  notional: number;
  status: string;
}

interface PortfolioCashFlow {
  portfolio_id: number;
  portfolio_name: string;
  current_nav: number;
  buys: number;
  sells: number;
  net_cash_flow: number;
  net_cash_flow_pct: number;
  buy_orders: number;
  sell_orders: number;
  orders: OrderDetail[];
}

interface CashFlowData {
  date: string;
  total_buys: number;
  total_sells: number;
  total_net_cash_flow: number;
  total_net_cash_flow_pct: number;
  portfolios: PortfolioCashFlow[];
}

const fmtCurrency = (v: number) =>
  v.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });

const fmtPct = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;

export default function NetCashFlow() {
  const [data, setData] = useState<CashFlowData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(dayjs());

  useEffect(() => {
    load(selectedDate.format('YYYY-MM-DD'));
  }, [selectedDate]);

  const load = async (dateStr: string) => {
    setLoading(true);
    try {
      const res = await getNetCashFlow(dateStr);
      setData(res.data);
    } catch {
      setData(null);
    }
    setLoading(false);
  };

  const portfolioColumns = [
    { title: 'Portfolio', dataIndex: 'portfolio_name', key: 'name' },
    {
      title: 'NAV',
      dataIndex: 'current_nav',
      key: 'nav',
      render: (v: number) => fmtCurrency(v),
    },
    {
      title: 'Buys',
      dataIndex: 'buys',
      key: 'buys',
      render: (v: number) => v > 0 ? <span style={{ color: '#ff4d4f' }}>({fmtCurrency(v)})</span> : '—',
    },
    {
      title: 'Sells',
      dataIndex: 'sells',
      key: 'sells',
      render: (v: number) => v > 0 ? <span style={{ color: '#52c41a' }}>{fmtCurrency(v)}</span> : '—',
    },
    {
      title: 'Net Cash Flow',
      dataIndex: 'net_cash_flow',
      key: 'net',
      render: (v: number) => (
        <strong style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f' }}>
          {fmtCurrency(v)}
        </strong>
      ),
    },
    {
      title: '% of NAV',
      dataIndex: 'net_cash_flow_pct',
      key: 'pct',
      render: (v: number) => (
        <Tag color={v >= 0 ? 'green' : 'red'}>
          {fmtPct(v)}
        </Tag>
      ),
    },
    {
      title: 'Orders',
      key: 'orders_count',
      render: (_: unknown, record: PortfolioCashFlow) => (
        <Space size={4}>
          {record.buy_orders > 0 && <Tag color="red">{record.buy_orders} buy</Tag>}
          {record.sell_orders > 0 && <Tag color="green">{record.sell_orders} sell</Tag>}
        </Space>
      ),
    },
  ];

  const expandedRowRender = (record: PortfolioCashFlow) => {
    const orderColumns = [
      { title: 'Ticker', dataIndex: 'ticker', key: 'ticker' },
      {
        title: 'Side',
        dataIndex: 'side',
        key: 'side',
        render: (v: string) => <Tag color={v === 'BUY' ? 'red' : 'green'}>{v}</Tag>,
      },
      { title: 'Shares', dataIndex: 'shares', key: 'shares', render: (v: number) => v.toLocaleString() },
      { title: 'Price', dataIndex: 'price', key: 'price', render: (v: number) => `$${v.toFixed(2)}` },
      {
        title: 'Notional',
        dataIndex: 'notional',
        key: 'notional',
        render: (v: number, row: OrderDetail) => (
          <span style={{ color: row.side === 'BUY' ? '#ff4d4f' : '#52c41a' }}>
            {row.side === 'BUY' ? `(${fmtCurrency(v)})` : fmtCurrency(v)}
          </span>
        ),
      },
      {
        title: 'Status',
        dataIndex: 'status',
        key: 'status',
        render: (v: string) => <Tag>{v}</Tag>,
      },
    ];

    return (
      <Table
        dataSource={record.orders}
        columns={orderColumns}
        rowKey="id"
        pagination={false}
        size="small"
      />
    );
  };

  const totalNet = data?.total_net_cash_flow ?? 0;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0, color: '#1a1a2e' }}>Net Cash Flow</h2>
        <DatePicker
          value={selectedDate}
          onChange={(d) => d && setSelectedDate(d)}
          allowClear={false}
        />
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} md={6}>
          <Card size="small" style={{ borderColor: '#e8e8e8' }}>
            <div style={{ color: '#666', fontSize: 12 }}>Total Buys (Outflow)</div>
            <div style={{ fontSize: 20, fontWeight: 600, color: '#ff4d4f' }}>
              <ArrowDownOutlined style={{ fontSize: 14, marginRight: 4 }} />
              {data ? fmtCurrency(data.total_buys) : '—'}
            </div>
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small" style={{ borderColor: '#e8e8e8' }}>
            <div style={{ color: '#666', fontSize: 12 }}>Total Sells (Inflow)</div>
            <div style={{ fontSize: 20, fontWeight: 600, color: '#52c41a' }}>
              <ArrowUpOutlined style={{ fontSize: 14, marginRight: 4 }} />
              {data ? fmtCurrency(data.total_sells) : '—'}
            </div>
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small" style={{ borderColor: '#e8e8e8' }}>
            <div style={{ color: '#666', fontSize: 12 }}>Net Cash Flow</div>
            <div style={{ fontSize: 20, fontWeight: 600, color: totalNet >= 0 ? '#52c41a' : '#ff4d4f' }}>
              {data ? fmtCurrency(totalNet) : '—'}
            </div>
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small" style={{ borderColor: '#e8e8e8' }}>
            <div style={{ color: '#666', fontSize: 12 }}>Net % of AUM</div>
            <div style={{ fontSize: 20, fontWeight: 600, color: totalNet >= 0 ? '#52c41a' : '#ff4d4f' }}>
              {data ? fmtPct(data.total_net_cash_flow_pct) : '—'}
            </div>
          </Card>
        </Col>
      </Row>

      <h3 style={{ color: '#1a1a2e', marginBottom: 12 }}>
        Per Portfolio ({data?.portfolios.length ?? 0})
      </h3>
      <Table
        dataSource={data?.portfolios ?? []}
        columns={portfolioColumns}
        rowKey="portfolio_id"
        loading={loading}
        pagination={false}
        size="small"
        expandable={{ expandedRowRender }}
        summary={() =>
          data && data.portfolios.length > 0 ? (
            <Table.Summary.Row>
              <Table.Summary.Cell index={0}><strong>Total</strong></Table.Summary.Cell>
              <Table.Summary.Cell index={1} />
              <Table.Summary.Cell index={2}>
                {data.total_buys > 0 && <strong style={{ color: '#ff4d4f' }}>({fmtCurrency(data.total_buys)})</strong>}
              </Table.Summary.Cell>
              <Table.Summary.Cell index={3}>
                {data.total_sells > 0 && <strong style={{ color: '#52c41a' }}>{fmtCurrency(data.total_sells)}</strong>}
              </Table.Summary.Cell>
              <Table.Summary.Cell index={4}>
                <strong style={{ color: totalNet >= 0 ? '#52c41a' : '#ff4d4f' }}>
                  {fmtCurrency(totalNet)}
                </strong>
              </Table.Summary.Cell>
              <Table.Summary.Cell index={5}>
                <Tag color={totalNet >= 0 ? 'green' : 'red'}>{fmtPct(data.total_net_cash_flow_pct)}</Tag>
              </Table.Summary.Cell>
              <Table.Summary.Cell index={6} />
            </Table.Summary.Row>
          ) : null
        }
      />

      {data && data.portfolios.length === 0 && !loading && (
        <p style={{ color: '#999', textAlign: 'center', marginTop: 32 }}>
          No orders for {selectedDate.format('MMM D, YYYY')}.
        </p>
      )}
    </div>
  );
}
