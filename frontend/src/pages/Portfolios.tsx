import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, InputNumber, DatePicker, Select, Space, Tag, message } from 'antd';
import { PlusOutlined, ClusterOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { getDashboardSummary, createPortfolio, createCluster, deletePortfolio } from '../services/api';
import type { PortfolioSummary } from '../types';


export default function Portfolios() {
  const [portfolios, setPortfolios] = useState<PortfolioSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [clusterModalOpen, setClusterModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [clusterForm] = Form.useForm();
  const navigate = useNavigate();

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    setLoading(true);
    try {
      const res = await getDashboardSummary();
      // Strip empty children arrays so Ant Design doesn't show expand icons
      const clean = (list: PortfolioSummary[]): PortfolioSummary[] =>
        list.map(p => ({
          ...p,
          children: p.children && p.children.length > 0 ? clean(p.children) : undefined as unknown as PortfolioSummary[],
        }));
      setPortfolios(clean(res.data));
    } catch {
      message.error('Failed to load portfolios');
    }
    setLoading(false);
  };

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      await createPortfolio({
        name: values.name,
        beginning_nav: values.beginning_nav,
        beginning_date: values.beginning_date.format('YYYY-MM-DD'),
        benchmark_ticker: values.benchmark_ticker || undefined,
        entity_type: values.entity_type || 'fund',
      });
      message.success('Portfolio created');
      setModalOpen(false);
      form.resetFields();
      load();
    } catch {
      // validation error
    }
  };

  const handleCreateCluster = async () => {
    try {
      const values = await clusterForm.validateFields();
      await createCluster({
        name: values.name,
        benchmark_ticker: values.benchmark_ticker || undefined,
      });
      message.success('Cluster created');
      setClusterModalOpen(false);
      clusterForm.resetFields();
      load();
    } catch {
      // validation error
    }
  };

  const handleDelete = async (id: number) => {
    await deletePortfolio(id);
    message.success('Portfolio deleted');
    load();
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: PortfolioSummary) => (
        <Space>
          <a onClick={() => navigate(`/portfolios/${record.id}`)} style={{ color: '#1a1a2e' }}>
            {name}
          </a>
          {record.portfolio_type === 'parent' && <Tag color="blue"><ClusterOutlined /> Cluster</Tag>}
        </Space>
      ),
    },
    {
      title: 'Beginning NAV',
      dataIndex: 'beginning_nav',
      key: 'beginning_nav',
      render: (v: number, record: PortfolioSummary) =>
        record.portfolio_type === 'parent' ? '—' : v.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }),
    },
    {
      title: 'Current NAV',
      dataIndex: 'current_nav',
      key: 'current_nav',
      render: (v: number) => v.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }),
    },
    {
      title: 'NAV/Unit',
      dataIndex: 'nav_per_unit',
      key: 'nav_per_unit',
      render: (v: number, record: PortfolioSummary) =>
        record.portfolio_type === 'parent' ? '—' : v.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }),
    },
    {
      title: 'YTD Return',
      key: 'return',
      render: (_: unknown, record: PortfolioSummary) => {
        if (record.portfolio_type === 'parent') return '—';
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
      title: 'Equity Exposure',
      dataIndex: 'equity_exposure',
      key: 'equity_exposure',
      render: (v: number) => `${v.toFixed(1)}%`,
    },
    {
      title: 'Benchmark',
      dataIndex: 'benchmark_ticker',
      key: 'benchmark_ticker',
      render: (v: string | null) => v || '—',
    },
    {
      title: '',
      key: 'actions',
      render: (_: unknown, record: PortfolioSummary) => (
        <Button type="link" size="small" onClick={() => handleDelete(record.id)} style={{ color: '#666' }}>
          Delete
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0, color: '#1a1a2e' }}>Portfolios</h2>
        <Space>
          <Button icon={<ClusterOutlined />} onClick={() => setClusterModalOpen(true)}>
            New Cluster
          </Button>
          <Button icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
            New Portfolio
          </Button>
        </Space>
      </div>

      <Table
        dataSource={portfolios}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={false}
        size="middle"
      />

      <Modal
        title="Create Portfolio"
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => setModalOpen(false)}
        okText="Create"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="Portfolio Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="beginning_nav" label="Beginning NAV" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} min={0} formatter={(v) => `$ ${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} />
          </Form.Item>
          <Form.Item name="beginning_date" label="Beginning Date" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="benchmark_ticker" label="Benchmark Ticker (optional)">
            <Input placeholder="e.g., ^GSPC for S&P 500" />
          </Form.Item>
          <Form.Item name="entity_type" label="Type" initialValue="fund">
            <Select options={[{ label: 'Fund', value: 'fund' }, { label: 'Client', value: 'client' }]} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Create Cluster"
        open={clusterModalOpen}
        onOk={handleCreateCluster}
        onCancel={() => setClusterModalOpen(false)}
        okText="Create"
      >
        <Form form={clusterForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="Cluster Name" rules={[{ required: true }]}>
            <Input placeholder="e.g., Equity Mandate" />
          </Form.Item>
          <Form.Item name="benchmark_ticker" label="Benchmark Ticker (optional)">
            <Input placeholder="e.g., ^GSPC for S&P 500" />
          </Form.Item>
          <p style={{ color: '#666', fontSize: 12, margin: 0 }}>
            A cluster groups portfolios that follow the same orders. You can add members after creating it.
          </p>
        </Form>
      </Modal>
    </div>
  );
}
