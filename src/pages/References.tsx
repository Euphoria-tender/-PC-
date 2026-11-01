/**
 * 文化DNA —— 本地图库页（联网参考图）
 * 展示联网搜索入库的参考图片，随每次「联网鉴定」自动扩充
 */
import { useEffect, useState, useCallback } from 'react';
import { Table, Tag, Button, Card, Typography, Space, Input, Image, Empty } from 'antd';
import { ReloadOutlined, GlobalOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { listReferencesApi, ReferenceItem } from '../api/references';
import PageHeader from '../components/PageHeader';
import { imgUrl } from '../utils/host';

const { Text } = Typography;

export default function References() {
  const [data, setData] = useState<ReferenceItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [total, setTotal] = useState(0);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 12, total: 0 });

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listReferencesApi({
        page: pagination.current,
        page_size: pagination.pageSize,
        keyword,
      }) as any;
      setData(res?.items ?? []);
      setPagination(prev => ({ ...prev, total: res?.pagination?.total ?? 0 }));
      setTotal(res?.total_references ?? 0);
    } catch { /* 拦截器已处理 */ }
    finally { setLoading(false); }
  }, [pagination.current, pagination.pageSize, keyword]);

  useEffect(() => { fetchList(); }, [fetchList]);

  const columns: ColumnsType<ReferenceItem> = [
    {
      title: '参考图',
      dataIndex: 'image_url',
      key: 'image_url',
      width: 90,
      render: (url: string) => (
        <Image
          src={imgUrl(url)}
          width={64}
          height={64}
          style={{ objectFit: 'cover', borderRadius: 4 }}
          fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        />
      ),
    },
    { title: '关键词', dataIndex: 'query', key: 'query', width: 140, render: (q: string) => <Tag color="gold">{q}</Tag> },
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true, render: (t: string) => t || '-' },
    { title: '来源', dataIndex: 'source', key: 'source', width: 90 },
    {
      title: '原始链接',
      dataIndex: 'source_url',
      key: 'source_url',
      ellipsis: true,
      render: (u: string) => (u ? <a href={u} target="_blank" rel="noreferrer" style={{ fontSize: 12 }}><GlobalOutlined /> 查看</a> : '-'),
    },
    { title: '入库时间', dataIndex: 'created_at', key: 'created_at', width: 170 },
  ];

  return (
    <>
      <PageHeader title="本地图库" subtitle="联网搜索自动入库的参考图片" />
      <Card
        className="soft-card"
        extra={
        <Space wrap>
          <Text type="secondary">已收录 {total} 张</Text>
          <Input.Search
            placeholder="按关键词/标题搜索"
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
        locale={{ emptyText: <Empty description="本地图库为空，去「AI 识别 → 本地+联网鉴定」搜索一次即可自动入库" /> }}
        pagination={{
          ...pagination,
          showSizeChanger: true,
          showTotal: t => `共 ${t} 张参考图`,
          onChange: (page, pageSize) => setPagination(prev => ({ ...prev, current: page, pageSize })),
        }}
        scroll={{ x: 900 }}
      />
      </Card>
    </>
  );
}