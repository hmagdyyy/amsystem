import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Table, Row, Col, Button, Space, Modal, Form, InputNumber, DatePicker, Select, message, Spin, Tag } from 'antd';
import { ArrowLeftOutlined, DownloadOutlined, SyncOutlined, EditOutlined, ClusterOutlined, PlusOutlined } from '@ant-design/icons';
import {
  getPortfolio,
  getPortfolioStats,
  getHoldings,
  getSectorBreakdown,
  addCashFlow,
  takeSnapshot,
  refreshPrices,
  exportHoldingsUrl,
  updatePortfolio,
  getSubPortfolios,
  getPortfolios,
  addMember,
  removeMember,
} from '../services/api';
import type { Portfolio, Holding, SectorBreakdown } from '../types';

export default function PortfolioDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [sectors, setSectors] = useState<SectorBreakdown[]>([]);
  const [loading, setLoading] = useState(true);
  const [cfModalOpen, setCfModalOpen] = useState(false);
  const [cfForm] = Form.useForm();
  const [refreshing, setRefreshing] = useState(false);
  const [stats, setStats] = useState<{ total_return: number; benchmark_return: number | null; equity_exposure: number; funds_exposure: number } | null>(null);
  const [navModalOpen, setNavModalOpen] = useState(false);
  const [navForm] = Form.useForm();
  const [members, setMembers] = useState<Portfolio[]>([]);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [availablePortfolios, setAvailablePortfolios] = useState<Portfolio[]>([]);
  const [selectedMemberId, setSelectedMemberId] = useState<number | null>(null);

  const portfolioId = Number(id);

  useEffect(() => {
    load();
  }, [id]);

  const load = async () => {
    setLoading(true);
    try {
      const [pRes, hRes, sRes, stRes] = await Promise.all([
        getPortfolio(portfolioId),
        getHoldings(portfolioId),
        getSectorBreakdown(portfolioId),
        getPortfolioStats(portfolioId),
      ]);
      setPortfolio(pRes.data);
      setHoldings(hRes.data);
      setSectors(sRes.data);
      setStats(stRes.data);

      if (pRes.data.portfolio_type === 'parent') {
        const subRes = await getSubPortfolios(portfolioId);
        setMembers(subRes.data);
      } else {
        setMembers([]);
      }
    } catch {
      message.error('Failed to load portfolio');
    }
    setLoading(false);
  };

  const handleCashFlow = async () => {
    let values;
    try {
      values = await cfForm.validateFields();
    } catch {
      return;
    }
    try {
      await addCashFlow({
        portfolio_id: portfolioId,
        date: values.date.format('YYYY-MM-DD'),
        type: values.type,
        amount: values.amount,
      });
      message.success('Cash flow recorded');
      setCfModalOpen(false);
      cfForm.resetFields();
      load();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || 'Failed to record cash flow');
    }
  };

  const handleSnapshot = async () => {
    await takeSnapshot(portfolioId);
    message.success('NAV snapshot taken');
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const res = await refreshPrices(portfolioId);
      message.success(`${res.data.updated} prices updated`);
      load();
    } catch {
      message.error('Failed to refresh prices');
    }
    setRefreshing(false);
  };

  const handleOpenAddModal = async () => {
    try {
      const res = await getPortfolios();
      const memberIds = new Set(members.map(m => m.id));
      setAvailablePortfolios(
        res.data.filter(p =>
          p.id !== portfolioId &&
          p.portfolio_type !== 'parent' &&
          !p.parent_id &&
          !memberIds.has(p.id)
        )
      );
      setSelectedMemberId(null);
      setAddModalOpen(true);
    } catch {
      message.error('Failed to load portfolios');
    }
  };

  const handleAddMember = async () => {
    if (!selectedMemberId) return;
    try {
      await addMember(portfolioId, selectedMemberId);
      message.success('Portfolio added to cluster');
      setAddModalOpen(false);
      load();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || 'Failed to add portfolio');
    }
  };

  const handleRemoveMember = async (memberId: number) => {
    try {
      await removeMember(memberId);
      message.success('Portfolio removed from cluster');
      load();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || 'Failed to remove portfolio');
    }
  };

  const handleNavEdit = async () => {
    try {
      const values = await navForm.validateFields();
      const update: { beginning_nav?: number; beginning_nav_per_unit?: number; entity_type?: string } = {};
      if (values.beginning_nav !== undefined) update.beginning_nav = values.beginning_nav;
      if (values.beginning_nav_per_unit !== undefined) update.beginning_nav_per_unit = values.beginning_nav_per_unit;
      if (values.entity_type !== undefined) update.entity_type = values.entity_type;
      await updatePortfolio(portfolioId, update);
      message.success('Portfolio settings updated');
      setNavModalOpen(false);
      load();
    } catch {
      // validation
    }
  };

  if (loading) return <Spin size="large" />;
  if (!portfolio) return <div>Portfolio not found</div>;

  const isCluster = portfolio.portfolio_type === 'parent';
  const totalMemberNav = members.reduce((s, m) => s + m.current_nav, 0);

  const holdingColumns = [
    { title: 'Ticker', dataIndex: 'ticker', key: 'ticker', width: 100 },
    { title: 'Sector', dataIndex: 'sector', key: 'sector', render: (v: string | null) => v || '—' },
    { title: 'Shares', dataIndex: 'shares', key: 'shares', render: (v: number) => v.toLocaleString() },
    {
      title: 'Cost/Share',
      dataIndex: 'cost_per_share',
      key: 'cost_per_share',
      render: (v: number) => `$${v.toFixed(2)}`,
    },
    {
      title: 'Mkt Price',
      dataIndex: 'market_price',
      key: 'market_price',
      render: (v: number) => `$${v.toFixed(2)}`,
    },
    {
      title: 'Mkt Value',
      dataIndex: 'market_value',
      key: 'market_value',
      render: (v: number) => v.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }),
    },
    { title: 'Weight %', dataIndex: 'weight', key: 'weight', render: (v: number) => `${v.toFixed(2)}%` },
    { title: 'Return %', dataIndex: 'return_pct', key: 'return_pct', render: (v: number) => `${v.toFixed(2)}%` },
  ];

  const sectorColumns = [
    { title: 'Sector', dataIndex: 'sector', key: 'sector' },
    { title: 'Weight %', dataIndex: 'weight', key: 'weight', render: (v: number) => `${v.toFixed(2)}%` },
  ];

  const memberColumns = [
    {
      title: 'Portfolio',
      dataIndex: 'name',
      key: 'name',
      sorter: (a: Portfolio, b: Portfolio) => a.name.localeCompare(b.name),
      render: (name: string, record: Portfolio) => (
        <a onClick={() => navigate(`/portfolios/${record.id}`)} style={{ color: '#1a1a2e' }}>{name}</a>
      ),
    },
    {
      title: 'NAV',
      dataIndex: 'current_nav',
      key: 'current_nav',
      sorter: (a: Portfolio, b: Portfolio) => a.current_nav - b.current_nav,
      render: (v: number) => v.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }),
    },
    {
      title: 'Weight',
      key: 'weight',
      sorter: (a: Portfolio, b: Portfolio) => a.current_nav - b.current_nav,
      render: (_: unknown, record: Portfolio) =>
        totalMemberNav > 0
          ? `${(record.current_nav / totalMemberNav * 100).toFixed(2)}%`
          : '—',
    },
    {
      title: 'Type',
      dataIndex: 'entity_type',
      key: 'entity_type',
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: 'NAV/Unit',
      dataIndex: 'nav_per_unit',
      key: 'nav_per_unit',
      render: (v: number) => v.toFixed(2),
    },
    {
      title: '',
      key: 'action',
      render: (_: unknown, record: Portfolio) => (
        <Button type="link" size="small" danger onClick={() => handleRemoveMember(record.id)}>
          Remove
        </Button>
      ),
    },
  ];

  // --- Cluster view ---
  if (isCluster) {
    return (
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/portfolios')} />
            <h2 style={{ margin: 0, color: '#1a1a2e' }}>{portfolio.name}</h2>
            <Tag icon={<ClusterOutlined />} color="blue">Cluster — {members.length} portfolios</Tag>
          </Space>
          <Space>
            <Button icon={<DownloadOutlined />} href={exportHoldingsUrl(portfolioId)}>
              Export CSV
            </Button>
          </Space>
        </div>

        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={12} md={6}>
            <Card size="small" style={{ borderColor: '#e8e8e8' }}>
              <div style={{ color: '#666', fontSize: 12 }}>Total AUM</div>
              <div style={{ fontSize: 20, fontWeight: 600, color: '#1a1a2e' }}>
                {totalMemberNav.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })}
              </div>
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card size="small" style={{ borderColor: '#e8e8e8' }}>
              <div style={{ color: '#666', fontSize: 12 }}>Members</div>
              <div style={{ fontSize: 20, fontWeight: 600, color: '#1a1a2e' }}>{members.length}</div>
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card size="small" style={{ borderColor: '#e8e8e8' }}>
              <div style={{ color: '#666', fontSize: 12 }}>Equity Exposure</div>
              <div style={{ fontSize: 20, fontWeight: 600, color: '#1a1a2e' }}>
                {stats ? `${stats.equity_exposure.toFixed(2)}%` : '—'}
              </div>
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card size="small" style={{ borderColor: '#e8e8e8' }}>
              <div style={{ color: '#666', fontSize: 12 }}>Benchmark</div>
              <div style={{ fontSize: 20, fontWeight: 600, color: '#1a1a2e' }}>
                {portfolio.benchmark_ticker || '—'}
              </div>
            </Card>
          </Col>
        </Row>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h3 style={{ color: '#1a1a2e', margin: 0 }}>
            <ClusterOutlined style={{ marginRight: 8 }} />
            Member Portfolios ({members.length})
          </h3>
          <Button icon={<PlusOutlined />} size="small" onClick={handleOpenAddModal}>Add Portfolio</Button>
        </div>
        {members.length > 0 ? (
          <Table
            dataSource={members}
            columns={memberColumns}
            rowKey="id"
            pagination={false}
            size="small"
            style={{ marginBottom: 32 }}
            summary={() => (
              <Table.Summary.Row>
                <Table.Summary.Cell index={0}><strong>Total</strong></Table.Summary.Cell>
                <Table.Summary.Cell index={1}>
                  <strong>{totalMemberNav.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })}</strong>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={2}><strong>100%</strong></Table.Summary.Cell>
                <Table.Summary.Cell index={3} />
                <Table.Summary.Cell index={4} />
                <Table.Summary.Cell index={5} />
              </Table.Summary.Row>
            )}
          />
        ) : (
          <p style={{ color: '#999', marginBottom: 32 }}>No members yet. Add portfolios that follow the same orders.</p>
        )}

        {holdings.length > 0 && (
          <>
            <h3 style={{ color: '#1a1a2e', marginBottom: 12 }}>Consolidated Holdings ({holdings.length})</h3>
            <Table
              dataSource={holdings}
              columns={holdingColumns}
              rowKey="id"
              pagination={false}
              size="small"
              style={{ marginBottom: 32 }}
            />
          </>
        )}

        <Modal
          title="Add Portfolio to Cluster"
          open={addModalOpen}
          onOk={handleAddMember}
          onCancel={() => setAddModalOpen(false)}
          okText="Add"
          okButtonProps={{ disabled: !selectedMemberId }}
        >
          <p style={{ color: '#666', marginBottom: 16 }}>
            Select a portfolio to add to <strong>{portfolio.name}</strong>.
          </p>
          <Select
            style={{ width: '100%' }}
            placeholder="Select portfolio"
            value={selectedMemberId}
            onChange={setSelectedMemberId}
            showSearch
            optionFilterProp="label"
            options={availablePortfolios.map(p => ({
              label: `${p.name} — NAV ${p.current_nav.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
              value: p.id,
            }))}
          />
        </Modal>
      </div>
    );
  }

  // --- Regular portfolio view ---
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/portfolios')} />
          <h2 style={{ margin: 0, color: '#1a1a2e' }}>{portfolio.name}</h2>
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => {
              navForm.setFieldsValue({
                beginning_nav: portfolio.beginning_nav || undefined,
                beginning_nav_per_unit: portfolio.beginning_nav_per_unit || undefined,
                entity_type: portfolio.entity_type || 'fund',
              });
              setNavModalOpen(true);
            }}
          />
        </Space>
        <Space>
          <Button icon={<SyncOutlined spin={refreshing} />} onClick={handleRefresh}>
            Refresh Prices
          </Button>
          <Button onClick={handleSnapshot}>Take NAV Snapshot</Button>
          <Button onClick={() => setCfModalOpen(true)}>Record Cash Flow</Button>
          <Button icon={<DownloadOutlined />} href={exportHoldingsUrl(portfolioId)}>
            Export CSV
          </Button>
        </Space>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} md={8}>
          <Card size="small" style={{ borderColor: '#e8e8e8' }}>
            <div style={{ color: '#666', fontSize: 12 }}>Current NAV</div>
            <div style={{ fontSize: 20, fontWeight: 600, color: '#1a1a2e' }}>
              {portfolio.current_nav.toLocaleString('en-US', { maximumFractionDigits: 0 })}
            </div>
          </Card>
        </Col>
        <Col xs={12} md={8}>
          <Card size="small" style={{ borderColor: '#e8e8e8' }}>
            <div style={{ color: '#666', fontSize: 12 }}>NAV/Unit</div>
            <div style={{ fontSize: 20, fontWeight: 600, color: '#1a1a2e' }}>
              {portfolio.nav_per_unit.toFixed(2)}
            </div>
          </Card>
        </Col>
        <Col xs={12} md={8}>
          <Card size="small" style={{ borderColor: '#e8e8e8' }}>
            <div style={{ color: '#666', fontSize: 12 }}>Total Units</div>
            <div style={{ fontSize: 20, fontWeight: 600, color: '#1a1a2e' }}>
              {portfolio.total_units.toLocaleString('en-US', { maximumFractionDigits: 2 })}
            </div>
          </Card>
        </Col>
        <Col xs={12} md={8}>
          <Card size="small" style={{ borderColor: '#e8e8e8' }}>
            <div style={{ color: '#666', fontSize: 12 }}>Total Return vs Benchmark</div>
            <div style={{ fontSize: 20, fontWeight: 600, color: '#1a1a2e' }}>
              <span style={{ color: stats && stats.total_return >= 0 ? '#52c41a' : '#ff4d4f' }}>
                {stats ? `${stats.total_return >= 0 ? '+' : ''}${stats.total_return.toFixed(2)}%` : '—'}
              </span>
              {stats?.benchmark_return != null && (
                <span style={{ fontSize: 13, color: '#666', marginLeft: 6 }}>
                  vs {stats.benchmark_return >= 0 ? '+' : ''}{stats.benchmark_return.toFixed(2)}%
                </span>
              )}
            </div>
          </Card>
        </Col>
        <Col xs={12} md={4}>
          <Card size="small" style={{ borderColor: '#e8e8e8' }}>
            <div style={{ color: '#666', fontSize: 12 }}>Equity Exposure</div>
            <div style={{ fontSize: 20, fontWeight: 600, color: '#1a1a2e' }}>
              {stats ? `${stats.equity_exposure.toFixed(2)}%` : '—'}
            </div>
          </Card>
        </Col>
        <Col xs={12} md={4}>
          <Card size="small" style={{ borderColor: '#e8e8e8' }}>
            <div style={{ color: '#666', fontSize: 12 }}>Funds Exposure</div>
            <div style={{ fontSize: 20, fontWeight: 600, color: '#1a1a2e' }}>
              {stats ? `${stats.funds_exposure.toFixed(2)}%` : '—'}
            </div>
          </Card>
        </Col>
      </Row>

      <h3 style={{ color: '#1a1a2e', marginBottom: 12 }}>Holdings ({holdings.length})</h3>
      <Table
        dataSource={holdings}
        columns={holdingColumns}
        rowKey="id"
        pagination={false}
        size="small"
        style={{ marginBottom: 32 }}
      />

      {sectors.length > 0 && (
        <>
          <h3 style={{ color: '#1a1a2e', marginBottom: 12 }}>Sector Breakdown</h3>
          <Table
            dataSource={sectors}
            columns={sectorColumns}
            rowKey="sector"
            pagination={false}
            size="small"
            style={{ maxWidth: 400 }}
          />
        </>
      )}

      <Modal
        title="Record Cash Flow"
        open={cfModalOpen}
        onOk={handleCashFlow}
        onCancel={() => setCfModalOpen(false)}
        okText="Record"
      >
        <Form form={cfForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="type" label="Type" rules={[{ required: true }]}>
            <Select options={[{ label: 'Injection', value: 'INJECTION' }, { label: 'Withdrawal', value: 'WITHDRAWAL' }]} />
          </Form.Item>
          <Form.Item name="amount" label="Amount" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} min={0} />
          </Form.Item>
          <Form.Item name="date" label="Date" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Edit Portfolio Settings"
        open={navModalOpen}
        onOk={handleNavEdit}
        onCancel={() => setNavModalOpen(false)}
        okText="Save"
      >
        <Form form={navForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="entity_type"
            label="Type"
            rules={[{ required: true }]}
          >
            <Select options={[{ label: 'Fund', value: 'fund' }, { label: 'Client', value: 'client' }]} />
          </Form.Item>
          <Form.Item
            name="beginning_nav"
            label="Beginning NAV"
          >
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              step={1000}
              formatter={(v) => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={(v) => Number((v || '').replace(/,/g, '')) as unknown as 0}
            />
          </Form.Item>
          <Form.Item
            name="beginning_nav_per_unit"
            label="Beginning NAV/Unit (IC Price at inception)"
          >
            <InputNumber style={{ width: '100%' }} min={0} step={0.01} />
          </Form.Item>
          <p style={{ color: '#666', fontSize: 12, margin: 0 }}>
            Fund: return uses IC price (NAV/Unit). Client: return uses Beginning NAV → Current NAV.
          </p>
        </Form>
      </Modal>
    </div>
  );
}
