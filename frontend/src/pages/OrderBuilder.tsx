import { useEffect, useState } from 'react';
import { Form, Input, InputNumber, Select, Button, Card, Table, Divider, Space, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { getPortfolios, createOrder, quickOrder } from '../services/api';
import type { Portfolio, Order } from '../types';

export default function OrderBuilder() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [form] = Form.useForm();
  const [quickForm] = Form.useForm();
  const [mode, setMode] = useState<'standard' | 'quick'>('standard');

  useEffect(() => {
    loadPortfolios();
  }, []);

  const loadPortfolios = async () => {
    try {
      const res = await getPortfolios();
      setPortfolios(res.data);
    } catch {
      // ignore
    }
  };

  const handleStandardOrder = async () => {
    try {
      const values = await form.validateFields();
      const res = await createOrder({
        portfolio_id: values.portfolio_id,
        ticker: values.ticker.toUpperCase(),
        target_weight: values.target_weight,
        price: values.price,
      });
      setOrders([res.data, ...orders]);
      message.success(`Order created: ${res.data.bloomberg_message}`);
      form.resetFields(['ticker', 'target_weight', 'price']);
    } catch (err: any) {
      if (err.response?.data?.detail) {
        message.error(err.response.data.detail);
      }
    }
  };

  const handleQuickOrder = async () => {
    try {
      const values = await quickForm.validateFields();
      const res = await quickOrder({
        portfolio_id: values.portfolio_id,
        ticker: values.ticker.toUpperCase(),
        side: values.side,
        target_weight: values.target_weight,
        price: values.price || undefined,
      });
      setOrders([res.data, ...orders]);
      message.success(`Order: ${res.data.bloomberg_message}`);
      quickForm.resetFields(['ticker', 'side', 'target_weight', 'price']);
    } catch (err: any) {
      if (err.response?.data?.detail) {
        message.error(err.response.data.detail);
      }
    }
  };

  const copyBloomberg = (msg: string) => {
    navigator.clipboard.writeText(msg);
    message.success('Copied to clipboard');
  };

  const orderColumns = [
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
    { title: 'Current %', dataIndex: 'current_weight', key: 'current_weight', render: (v: number) => `${v}%` },
    {
      title: 'Bloomberg',
      dataIndex: 'bloomberg_message',
      key: 'bloomberg_message',
      render: (v: string | null) =>
        v ? (
          <Button type="link" size="small" onClick={() => copyBloomberg(v)} style={{ color: '#1a1a2e', padding: 0 }}>
            Copy
          </Button>
        ) : null,
    },
  ];

  const portfolioOptions = portfolios.map((p) => ({ label: p.name, value: p.id }));

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0, color: '#1a1a2e' }}>Order Builder</h2>
        <Space>
          <Button type={mode === 'standard' ? 'primary' : 'default'} onClick={() => setMode('standard')}>
            Standard
          </Button>
          <Button type={mode === 'quick' ? 'primary' : 'default'} onClick={() => setMode('quick')}>
            Quick Entry
          </Button>
        </Space>
      </div>

      {mode === 'standard' ? (
        <Card size="small" style={{ marginBottom: 24, borderColor: '#e8e8e8' }}>
          <Form form={form} layout="inline" onFinish={handleStandardOrder}>
            <Form.Item name="portfolio_id" rules={[{ required: true, message: 'Select portfolio' }]}>
              <Select placeholder="Portfolio" options={portfolioOptions} style={{ width: 180 }} />
            </Form.Item>
            <Form.Item name="ticker" rules={[{ required: true, message: 'Enter ticker' }]}>
              <Input placeholder="Ticker" style={{ width: 100 }} />
            </Form.Item>
            <Form.Item name="target_weight" rules={[{ required: true, message: 'Enter weight' }]}>
              <InputNumber placeholder="Target %" min={0} max={100} style={{ width: 110 }} />
            </Form.Item>
            <Form.Item name="price" rules={[{ required: true, message: 'Enter price' }]}>
              <InputNumber placeholder="Price" min={0} style={{ width: 110 }} />
            </Form.Item>
            <Form.Item>
              <Button htmlType="submit" icon={<PlusOutlined />}>
                Build Order
              </Button>
            </Form.Item>
          </Form>
        </Card>
      ) : (
        <Card size="small" style={{ marginBottom: 24, borderColor: '#e8e8e8' }}>
          <div style={{ marginBottom: 8, color: '#666', fontSize: 12 }}>
            Quick entry for morning meetings. Price is auto-fetched if left empty.
          </div>
          <Form form={quickForm} layout="inline" onFinish={handleQuickOrder}>
            <Form.Item name="portfolio_id" rules={[{ required: true }]}>
              <Select placeholder="Portfolio" options={portfolioOptions} style={{ width: 180 }} />
            </Form.Item>
            <Form.Item name="ticker" rules={[{ required: true }]}>
              <Input placeholder="Ticker" style={{ width: 100 }} />
            </Form.Item>
            <Form.Item name="side" rules={[{ required: true }]}>
              <Select
                placeholder="Side"
                options={[{ label: 'Buy', value: 'BUY' }, { label: 'Sell', value: 'SELL' }]}
                style={{ width: 90 }}
              />
            </Form.Item>
            <Form.Item name="target_weight" rules={[{ required: true }]}>
              <InputNumber placeholder="Target %" min={0} max={100} style={{ width: 110 }} />
            </Form.Item>
            <Form.Item name="price">
              <InputNumber placeholder="Price (opt)" min={0} style={{ width: 120 }} />
            </Form.Item>
            <Form.Item>
              <Button htmlType="submit" icon={<PlusOutlined />}>
                Add
              </Button>
            </Form.Item>
          </Form>
        </Card>
      )}

      {orders.length > 0 && (
        <>
          <Divider />
          <h3 style={{ color: '#1a1a2e', marginBottom: 12 }}>Session Orders ({orders.length})</h3>
          <Table
            dataSource={orders}
            columns={orderColumns}
            rowKey="id"
            pagination={false}
            size="small"
          />
        </>
      )}
    </div>
  );
}
