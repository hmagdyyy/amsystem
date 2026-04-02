import { useState, useEffect } from 'react';
import { Upload as AntUpload, Table, message, Card, Button, Divider } from 'antd';
import { InboxOutlined, UploadOutlined } from '@ant-design/icons';
import { uploadExcel, uploadConsolidated, getUploadHistory } from '../services/api';
import type { UploadResult, UploadLog } from '../types';

const { Dragger } = AntUpload;

export default function Upload() {
  const [result, setResult] = useState<UploadResult | null>(null);
  const [uploading, setUploading] = useState(false);
  const [history, setHistory] = useState<UploadLog[]>([]);

  // Consolidated upload state
  const [clientFilterFile, setClientFilterFile] = useState<File | null>(null);
  const [consolidatedFile, setConsolidatedFile] = useState<File | null>(null);
  const [consolidatedUploading, setConsolidatedUploading] = useState(false);
  const [consolidatedResult, setConsolidatedResult] = useState<{
    portfolios_updated: number;
    total_holdings: number;
    skipped_sheets: number;
    total_sheets_in_file: number;
  } | null>(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const res = await getUploadHistory();
      setHistory(res.data);
    } catch {
      // ignore
    }
  };

  const handleUpload = (file: File) => {
    setUploading(true);
    uploadExcel(file)
      .then((res) => {
        setResult(res.data);
        message.success(`Updated ${res.data.portfolios_updated} portfolio(s) with ${res.data.total_holdings} holdings`);
        loadHistory();
      })
      .catch((err: any) => {
        message.error(err.response?.data?.detail || 'Upload failed');
      })
      .finally(() => {
        setUploading(false);
      });
    return false;
  };

  const handleConsolidatedUpload = async () => {
    if (!clientFilterFile || !consolidatedFile) {
      message.warning('Please select both the client list file and the consolidated file');
      return;
    }
    setConsolidatedUploading(true);
    try {
      const res = await uploadConsolidated(clientFilterFile, consolidatedFile);
      setConsolidatedResult(res.data);
      message.success(
        `Extracted ${res.data.portfolios_updated} portfolio(s) from ${res.data.total_sheets_in_file} sheets (${res.data.skipped_sheets} skipped)`
      );
      loadHistory();
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Consolidated upload failed');
    } finally {
      setConsolidatedUploading(false);
    }
  };

  const historyColumns = [
    { title: 'File', dataIndex: 'filename', key: 'filename' },
    { title: 'Records', dataIndex: 'records_processed', key: 'records_processed' },
    { title: 'Status', dataIndex: 'status', key: 'status' },
    {
      title: 'Uploaded',
      dataIndex: 'uploaded_at',
      key: 'uploaded_at',
      render: (v: string) => new Date(v).toLocaleString(),
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 24, color: '#1a1a2e' }}>Upload Portfolio Data</h2>

      <Card style={{ marginBottom: 24, borderColor: '#e8e8e8' }}>
        <Dragger
          accept=".xlsx,.xls,.pdf"
          showUploadList={false}
          beforeUpload={handleUpload}
          disabled={uploading}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined style={{ color: '#1a1a2e' }} />
          </p>
          <p style={{ color: '#1a1a2e' }}>Click or drag an Excel or PDF file here</p>
          <p style={{ color: '#999', fontSize: 12 }}>
            Supports Excel (.xlsx, .xls) and PDF portfolio statements
          </p>
        </Dragger>
      </Card>

      {result && (
        <Card size="small" style={{ marginBottom: 24, borderColor: '#e8e8e8' }}>
          <p style={{ margin: 0, color: '#1a1a2e' }}>
            Processed {result.portfolios_updated} portfolio(s), {result.total_holdings} holdings total
          </p>
        </Card>
      )}

      <Divider />

      <h2 style={{ marginBottom: 24, color: '#1a1a2e' }}>Consolidated Upload</h2>
      <p style={{ color: '#666', marginBottom: 16 }}>
        Upload a consolidated Excel file containing all portfolios, filtered by your client list.
        Only sheets matching names in the client list will be extracted.
      </p>

      <Card style={{ marginBottom: 24, borderColor: '#e8e8e8' }}>
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', marginBottom: 16 }}>
          <div style={{ flex: 1, minWidth: 250 }}>
            <div style={{ color: '#1a1a2e', fontWeight: 600, marginBottom: 8 }}>1. Client List File</div>
            <AntUpload
              accept=".xlsx,.xls"
              showUploadList={false}
              beforeUpload={(file) => {
                setClientFilterFile(file as unknown as File);
                return false;
              }}
            >
              <Button icon={<UploadOutlined />}>
                {clientFilterFile ? clientFilterFile.name : 'Select Client List'}
              </Button>
            </AntUpload>
            {clientFilterFile && (
              <span style={{ marginLeft: 8, color: '#52c41a', fontSize: 12 }}>Selected</span>
            )}
          </div>

          <div style={{ flex: 1, minWidth: 250 }}>
            <div style={{ color: '#1a1a2e', fontWeight: 600, marginBottom: 8 }}>2. Consolidated Portfolio File</div>
            <AntUpload
              accept=".xlsx,.xls"
              showUploadList={false}
              beforeUpload={(file) => {
                setConsolidatedFile(file as unknown as File);
                return false;
              }}
            >
              <Button icon={<UploadOutlined />}>
                {consolidatedFile ? consolidatedFile.name : 'Select Consolidated File'}
              </Button>
            </AntUpload>
            {consolidatedFile && (
              <span style={{ marginLeft: 8, color: '#52c41a', fontSize: 12 }}>Selected</span>
            )}
          </div>
        </div>

        <Button
          type="primary"
          onClick={handleConsolidatedUpload}
          loading={consolidatedUploading}
          disabled={!clientFilterFile || !consolidatedFile}
          style={{ backgroundColor: '#1a1a2e', borderColor: '#1a1a2e' }}
        >
          Upload & Extract
        </Button>
      </Card>

      {consolidatedResult && (
        <Card size="small" style={{ marginBottom: 24, borderColor: '#e8e8e8' }}>
          <p style={{ margin: 0, color: '#1a1a2e' }}>
            Extracted {consolidatedResult.portfolios_updated} portfolio(s) with{' '}
            {consolidatedResult.total_holdings} holdings from{' '}
            {consolidatedResult.total_sheets_in_file} sheets ({consolidatedResult.skipped_sheets} skipped)
          </p>
        </Card>
      )}

      <Divider />

      <h3 style={{ color: '#1a1a2e', marginBottom: 12 }}>Upload History</h3>
      <Table
        dataSource={history}
        columns={historyColumns}
        rowKey="id"
        pagination={false}
        size="small"
      />
    </div>
  );
}
