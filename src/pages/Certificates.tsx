/**
 * 文化DNA —— 存证管理页
 * 证书列表 + 状态标签 + 验证
 */
import { useEffect, useState, useCallback } from 'react';
import {
  Table, Tag, Button, Space, message, Typography, Card, Descriptions, Modal,
} from 'antd';
import {
  SafetyCertificateOutlined, ReloadOutlined, CheckCircleOutlined,
  CloseCircleOutlined, SyncOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  listCertificatesApi, verifyCertificateApi, CertificateItem,
} from '../api/certificates';
import PageHeader from '../components/PageHeader';

const { Text } = Typography;

/** 存证状态映射 */
const statusMap: Record<string, { color: string; label: string; icon: React.ReactNode }> = {
  pending: { color: 'processing', label: '待上链', icon: <SyncOutlined spin /> },
  success: { color: 'success', label: '已上链', icon: <CheckCircleOutlined /> },
  failed: { color: 'error', label: '上链失败', icon: <CloseCircleOutlined /> },
};

export default function Certificates() {
  const [data, setData] = useState<CertificateItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 12, total: 0 });

  // 验证弹窗
  const [verifyOpen, setVerifyOpen] = useState(false);
  const [verifyResult, setVerifyResult] = useState<any>(null);
  const [verifyLoading, setVerifyLoading] = useState(false);

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listCertificatesApi({
        page: pagination.current,
        page_size: pagination.pageSize,
      }) as any;
      const items = res?.items ?? [];
      const p = res?.pagination ?? {};
      setData(items);
      setPagination(prev => ({ ...prev, total: p.total || 0 }));
    } catch { /* */ }
    finally { setLoading(false); }
  }, [pagination.current, pagination.pageSize]);

  useEffect(() => { fetchList(); }, [fetchList]);

  // 验证证书
  const handleVerify = async (certificate_no: string) => {
    setVerifyLoading(true);
    setVerifyOpen(true);
    try {
      const res = await verifyCertificateApi(certificate_no) as any;
      setVerifyResult(res);
    } catch {
      setVerifyResult(null);
    }
    finally { setVerifyLoading(false); }
  };

  const columns: ColumnsType<CertificateItem> = [
    {
      title: '证书编号',
      dataIndex: 'certificate_no',
      key: 'certificate_no',
      width: 200,
      render: (no: string) => <Text copyable code>{no}</Text>,
    },
    { title: '作品名称', dataIndex: 'work_title', key: 'work_title', width: 150 },
    {
      title: '交易ID',
      dataIndex: 'tx_id',
      key: 'tx_id',
      width: 160,
      ellipsis: true,
      render: (tx: string) => tx ? <Text copyable style={{ fontSize: 12 }}>{tx.slice(0, 16)}...</Text> : '-',
    },
    {
      title: '区块高度',
      dataIndex: 'block_height',
      key: 'block_height',
      width: 100,
      align: 'center',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: string) => {
        const m = statusMap[s] || { color: 'default', label: s, icon: null };
        return <Tag color={m.color} icon={m.icon}>{m.label}</Tag>;
      },
    },
    {
      title: '存证时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (t: string) => t || '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Button
          size="small"
          icon={<SafetyCertificateOutlined />}
          onClick={() => handleVerify(record.certificate_no)}
          disabled={record.status !== 'success'}
        >
          验证
        </Button>
      ),
    },
  ];

  return (
    <>
      <PageHeader title="存证管理" subtitle="上链存证记录与证书验证" />
      <Card
        className="soft-card"
        extra={
          <Button icon={<ReloadOutlined />} onClick={fetchList}>刷新</Button>
        }
      >
        <Table
          rowKey="certificate_no"
          columns={columns}
          dataSource={data}
          loading={loading}
          size="middle"
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: t => `共 ${t} 条存证`,
            onChange: (page, pageSize) => {
              setPagination(prev => ({ ...prev, current: page, pageSize }));
            },
          }}
          scroll={{ x: 1000 }}
        />
      </Card>

      {/* 验证结果 Modal */}
      <Modal
        title="证书验证结果"
        open={verifyOpen}
        onCancel={() => setVerifyOpen(false)}
        footer={null}
        loading={verifyLoading}
      >
        {verifyResult ? (
          <Descriptions column={1} size="small">
            <Descriptions.Item label="证书编号">
              <Text copyable>{verifyResult.certificate_no}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="验证结果">
              {verifyResult.is_valid ? (
                <Tag color="success" icon={<CheckCircleOutlined />}>证书有效</Tag>
              ) : (
                <Tag color="error" icon={<CloseCircleOutlined />}>证书无效</Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="交易ID">
              <Text copyable style={{ fontSize: 12 }}>{verifyResult.db_record?.tx_id}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="区块高度">
              {verifyResult.db_record?.block_height}
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <Text type="secondary">验证失败，请稍后重试</Text>
        )}
      </Modal>
    </>
  );
}