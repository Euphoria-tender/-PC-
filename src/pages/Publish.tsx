/**
 * 文化DNA —— 网络发布/同步台账页
 * 展示作品「上传到网络」的存证记录（IPFS CID / 本地离线存证）
 */
import { useEffect, useState, useCallback } from 'react';
import { Table, Tag, Button, Card, Typography, Space, Input } from 'antd';
import {
  ReloadOutlined, CloudServerOutlined, DatabaseOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { listPublishApi, PublishRecord } from '../api/publish';
import PageHeader from '../components/PageHeader';
import { palette } from '../theme';

const { Text } = Typography;

/** 发布方式映射 */
const typeMap: Record<string, { color: string; label: string; icon: React.ReactNode }> = {
  ipfs: { color: palette.cinnabar, label: 'IPFS 网络', icon: <CloudServerOutlined /> },
  local: { color: palette.celadon, label: '本地离线存证', icon: <DatabaseOutlined /> },
};

export default function Publish() {
  const [data, setData] = useState<PublishRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [pagination, setPagination] = useState({ current: 1, pageSize: 12, total: 0 });

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listPublishApi({
        page: pagination.current,
        page_size: pagination.pageSize,
        keyword,
      }) as any;
      setData(res?.items ?? []);
      setPagination(prev => ({ ...prev, total: res?.pagination?.total ?? 0 }));
    } catch { /* 拦截器已处理 */ }
    finally { setLoading(false); }
  }, [pagination.current, pagination.pageSize, keyword]);

  useEffect(() => { fetchList(); }, [fetchList]);

  const columns: ColumnsType<PublishRecord> = [
    { title: '作品名称', dataIndex: 'work_title', key: 'work_title', width: 180 },
    {
      title: '作品编号',
      dataIndex: 'work_id',
      key: 'work_id',
      width: 130,
      ellipsis: true,
      render: (id: string) => <Text copyable style={{ fontSize: 12 }}>{id?.slice(0, 8)}...</Text>,
    },
    {
      title: '发布方式',
      dataIndex: 'publish_type',
      key: 'publish_type',
      width: 140,
      render: (t: string) => {
        const m = typeMap[t] || { color: 'default', label: t, icon: null };
        return <Tag color={m.color} icon={m.icon}>{m.label}</Tag>;
      },
    },
    {
      title: '存证标识',
      dataIndex: 'cid',
      key: 'cid',
      width: 240,
      ellipsis: true,
      render: (cid: string) => cid ? <Text copyable code style={{ fontSize: 12 }}>{cid}</Text> : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (s: string) => (s === 'success' ? <Tag color="success">成功</Tag> : <Tag color="error">{s}</Tag>),
    },
    { title: '发布时间', dataIndex: 'created_at', key: 'created_at', width: 170 },
  ];

  return (
    <>
      <PageHeader title="网络发布" subtitle="作品到 IPFS / 本地离线存证的发布台账" />
      <Card
        className="soft-card"
        extra={
          <Space wrap>
            <Input.Search
              placeholder="按作品名/CID 搜索"
              allowClear
              onSearch={(v) => { setKeyword(v); setPagination(prev => ({ ...prev, current: 1 })); }}
              style={{ width: 220 }}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchList}>刷新</Button>
          </Space>
        }
      >
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        size="middle"
        expandable={{
          expandedRowRender: (record) => (
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>可访问地址：</Text>
              <Text copyable code style={{ fontSize: 12 }}>{record.resource_url || '-'}</Text>
              {record.message && (
                <div style={{ marginTop: 6 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>说明：{record.message}</Text>
                </div>
              )}
            </div>
          ),
        }}
        pagination={{
          ...pagination,
          showSizeChanger: true,
          showTotal: t => `共 ${t} 条发布记录`,
          onChange: (page, pageSize) => setPagination(prev => ({ ...prev, current: page, pageSize })),
        }}
        scroll={{ x: 1000 }}
      />
      </Card>
    </>
  );
}