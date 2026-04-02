import { useEffect, useState } from 'react';
import { Table, Card, Row, Col, Select, Spin, Tag } from 'antd';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { getDashboardSummary, getChartData } from '../services/api';
import type { PortfolioSummary } from '../types';
import { useNavigate } from 'react-router-dom';

export default function Dashboard() {
  const [summaries, setSummaries] = useState<PortfolioSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPortfolio, setSelectedPortfolio] = useState<number | null>(null);
  const [chartData, setChartData] = useState<{ date: string; portfolio: number; benchmark: number }[]>([]);
  const [chartLoading, setChartLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    loadSummary();
  }, []);

  useEffect(() => {
    if (selectedPortfolio) {
      loadChart(selectedPortfolio);
    }
  }, [selectedPortfolio]);

  const loadSummary = async () => {
    setLoading(true);
    try {
      const res = await getDashboardSummary();
      setSummaries(res.data);
      if (res.data.length > 0 && !selectedPortfolio) {
        setSelectedPortfolio(res.data[0].id);
      }
    } catch {
      // silently handle
    }
    setLoading(false);
  };

  const loadChart = async (portfolioId: number) => {
    setChartLoading(true);
    try {
      const res = await getChartData(portfolioId);
      const pData = res.data.portfolio || [];
      const bData = res.data.benchmark || [];
      const bMap = new Map(bData.map((b: { date: string; value: number }) => [b.date, b.value]));
      const merged = pData.map((p: { date: string; value: number }) => ({
        date: p.date,
        portfolio: p.value,
        benchmark: bMap.get(p.date) ?? 0,
      }));
      setChartData(merged);
    } catch {
      setChartData([]);
    }
    setChartLoading(false);
  };

  const totalAUM = summaries.reduce((sum, s) => sum + s.current_nav, 0);

  // Build chart dropdown options including sub-portfolios
  const chartOptions: { label: string; value: number }[] = [];
  summaries.forEach((s) => {
    chartOptions.push({ label: s.name, value: s.id });
    if (s.children?.length) {
      s.children.forEach((c) => {
        chartOptions.push({ label: `  └ ${c.name}`, value: c.id });
      });
    }
  });

  const columns = [
    {
      title: 'Portfolio',
      dataIndex: 'name',
      key: 'name',
      sorter: (a: PortfolioSummary, b: PortfolioSummary) => a.name.localeCompare(b.name),
      render: (name: string, record: PortfolioSummary) => (
        <span>
          <a onClick={() => navigate(`/portfolios/${record.id}`)} style={{ color: '#1a1a2e' }}>
            {name}
          </a>
          {record.portfolio_type === 'parent' && (
            <Tag color="blue" style={{ marginLeft: 8, fontSize: 10 }}>Parent</Tag>
          )}
          <Tag
            color={record.entity_type === 'fund' ? 'green' : 'orange'}
            style={{ marginLeft: 4, fontSize: 10 }}
          >
            {record.entity_type === 'fund' ? 'Fund' : 'Client'}
          </Tag>
        </span>
      ),
    },
    {
      title: 'Beginning NAV',
      dataIndex: 'beginning_nav',
      key: 'beginning_nav',
      sorter: (a: PortfolioSummary, b: PortfolioSummary) => a.beginning_nav - b.beginning_nav,
      render: (v: number) => v.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }),
    },
    {
      title: 'Current NAV',
      dataIndex: 'current_nav',
      key: 'current_nav',
      sorter: (a: PortfolioSummary, b: PortfolioSummary) => a.current_nav - b.current_nav,
      render: (v: number) => v.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }),
    },
    {
      title: 'Return %',
      key: 'return',
      sorter: (a: PortfolioSummary, b: PortfolioSummary) => {
        const aVal = a.entity_type === 'fund' ? a.ytd_return : (a.nav_return ?? 0);
        const bVal = b.entity_type === 'fund' ? b.ytd_return : (b.nav_return ?? 0);
        return aVal - bVal;
      },
      render: (_: unknown, record: PortfolioSummary) => {
        const v = record.entity_type === 'fund' ? record.ytd_return : record.nav_return;
        if (v === null || v === undefined) return '—';
        return (
          <span style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f' }}>
            {v >= 0 ? '+' : ''}{v.toFixed(2)}%
          </span>
        );
      },
    },
    {
      title: 'Benchmark %',
      dataIndex: 'benchmark_return',
      key: 'benchmark_return',
      sorter: (a: PortfolioSummary, b: PortfolioSummary) => (a.benchmark_return ?? 0) - (b.benchmark_return ?? 0),
      render: (v: number | null) => (v !== null ? `${v.toFixed(2)}%` : '—'),
    },
    {
      title: 'Alpha',
      dataIndex: 'alpha',
      key: 'alpha',
      sorter: (a: PortfolioSummary, b: PortfolioSummary) => (a.alpha ?? 0) - (b.alpha ?? 0),
      render: (v: number | null) => (v !== null ? `${v.toFixed(2)}%` : '—'),
    },
    {
      title: 'Benchmark',
      dataIndex: 'benchmark_ticker',
      key: 'benchmark_ticker',
      render: (v: string | null) => v || '—',
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 24, color: '#1a1a2e' }}>Dashboard</h2>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card size="small" style={{ borderColor: '#e8e8e8' }}>
            <div style={{ color: '#666', fontSize: 12, marginBottom: 4 }}>Total AUM</div>
            <div style={{ fontSize: 24, fontWeight: 600, color: '#1a1a2e' }}>
              {totalAUM.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })}
            </div>
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" style={{ borderColor: '#e8e8e8' }}>
            <div style={{ color: '#666', fontSize: 12, marginBottom: 4 }}>Portfolios</div>
            <div style={{ fontSize: 24, fontWeight: 600, color: '#1a1a2e' }}>{summaries.length}</div>
          </Card>
        </Col>
      </Row>

      <Table
        dataSource={summaries}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={false}
        size="middle"
        style={{ marginBottom: 32 }}
        expandable={{
          expandedRowRender: (record) =>
            record.children?.length ? (
              <Table
                dataSource={record.children}
                columns={columns}
                rowKey="id"
                pagination={false}
                size="small"
                showHeader={false}
                style={{ margin: '-8px 0' }}
              />
            ) : null,
          rowExpandable: (record) => (record.children?.length ?? 0) > 0,
        }}
      />

      {summaries.length > 0 && (
        <div>
          <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ color: '#666' }}>Performance Chart:</span>
            <Select
              value={selectedPortfolio}
              onChange={setSelectedPortfolio}
              style={{ width: 240 }}
              options={chartOptions}
            />
          </div>
          {chartLoading ? (
            <Spin />
          ) : chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={360}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e8e8e8" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#666' }} />
                <YAxis tick={{ fontSize: 11, fill: '#666' }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="portfolio" stroke="#1a1a2e" strokeWidth={2} dot={false} name="Portfolio" />
                <Line type="monotone" dataKey="benchmark" stroke="#adb5bd" strokeWidth={2} dot={false} name="Benchmark" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ color: '#999', padding: 40, textAlign: 'center' }}>
              No NAV history data yet. Take a daily snapshot to start tracking performance.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
