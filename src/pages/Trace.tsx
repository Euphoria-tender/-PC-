/**
 * 文化DNA —— 溯源查询页
 * workId 查询 + 作品信息 + 溯源时间线
 */
import { useState } from 'react';
import {
  Card, Input, Button, Space, Descriptions, Timeline, Tag, Typography, Spin, Empty, message,
} from 'antd';
import {
  SearchOutlined, ClockCircleOutlined, CheckCircleOutlined,
  SwapOutlined, ScanOutlined,
} from '@ant-design/icons';
import { getTraceTimelineApi, TraceResult, TimelineEvent } from '../api/trace';
import PageHeader from '../components/PageHeader';
import { palette } from '../theme';

const { Text } = Typography;

/** 事件类型图标和颜色 */
const eventConfig: Record<string, { color: string; icon: React.ReactNode }> = {
  created: { color: palette.celadon, icon: <ClockCircleOutlined /> },
  dna_extracted: { color: palette.cinnabar, icon: <ScanOutlined /> },
  chain_record: { color: palette.success, icon: <CheckCircleOutlined /> },
  ownership_transfer: { color: palette.warning, icon: <SwapOutlined /> },
  verification: { color: palette.gold, icon: <SearchOutlined /> },
};

export default function Trace() {
  const [workId, setWorkId] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TraceResult | null>(null);
  const [error, setError] = useState('');

  const handleSearch = async () => {
    const trimmed = workId.trim();
    if (!trimmed) {
      message.warning('请输入作品编号');
      return;
    }
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const res = await getTraceTimelineApi(trimmed);
      setResult(res);
    } catch {
      setError('查询失败，请检查作品编号是否正确');
    }
    finally { setLoading(false); }
  };

  /** 根据事件类型渲染详情 */
  const renderEventDetail = (event: TimelineEvent) => {
    const d = event.detail;
    switch (event.event_type) {
      case 'created':
        return (
          <Descriptions size="small" column={2}>
            <Descriptions.Item label="作品名称">{d.title}</Descriptions.Item>
            <Descriptions.Item label="类别">{d.category}</Descriptions.Item>
            <Descriptions.Item label="创作者">{d.creator}</Descriptions.Item>
          </Descriptions>
        );
      case 'dna_extracted':
        return <Text copyable code style={{ fontSize: 12 }}>{d.dna_hash}</Text>;
      case 'chain_record':
        return (
          <Space direction="vertical" size={2}>
            <Text>证书编号: <Text code>{d.certificate_no}</Text></Text>
            <Text>交易ID: <Text copyable style={{ fontSize: 12 }}>{d.tx_id?.slice(0, 16)}...</Text></Text>
            <Text>区块高度: {d.block_height}</Text>
            <Tag color={d.status === 'success' ? 'green' : 'red'}>{d.status}</Tag>
          </Space>
        );
      case 'ownership_transfer':
        return (
          <Descriptions size="small" column={2}>
            <Descriptions.Item label="转让方ID">{d.from_owner_id}</Descriptions.Item>
            <Descriptions.Item label="受让方ID">{d.to_owner_id}</Descriptions.Item>
            <Descriptions.Item label="交易ID">
              <Text copyable style={{ fontSize: 12 }}>{d.tx_id?.slice(0, 16)}...</Text>
            </Descriptions.Item>
          </Descriptions>
        );
      case 'verification':
        return (
          <Descriptions size="small" column={2}>
            <Descriptions.Item label="鉴定类型">{d.verification_type}</Descriptions.Item>
            <Descriptions.Item label="AI匹配度">
              {d.ai_match_score != null ? `${(d.ai_match_score * 100).toFixed(1)}%` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="DNA验证">{d.dna_verified ? '通过' : '未通过'}</Descriptions.Item>
            <Descriptions.Item label="最终结果">
              <Tag color={d.final_result === 'authentic' ? 'green' : d.final_result === 'suspicious' ? 'orange' : 'red'}>
                {d.final_result === 'authentic' ? '真品' : d.final_result === 'suspicious' ? '存疑' : '赝品'}
              </Tag>
            </Descriptions.Item>
          </Descriptions>
        );
      default:
        return <Text type="secondary">{JSON.stringify(d)}</Text>;
    }
  };

  return (
    <>
      <PageHeader title="溯源查询" subtitle="通过作品编号追溯作品全生命周期" />

      <Card style={{ marginBottom: 24 }}>
        <Space size="middle">
          <Input
            placeholder="请输入作品编号（work_id）"
            value={workId}
            onChange={e => setWorkId(e.target.value)}
            onPressEnter={handleSearch}
            style={{ width: 360 }}
            allowClear
          />
          <Button type="primary" icon={<SearchOutlined />} loading={loading} onClick={handleSearch}>
            查询溯源
          </Button>
        </Space>
      </Card>

      <Spin spinning={loading}>
        {error && (
          <Card><Empty description={error} /></Card>
        )}

        {result && (
          <>
            {/* 作品基本信息 */}
            <Card title="作品信息" style={{ marginBottom: 24 }}>
              <Descriptions column={2}>
                <Descriptions.Item label="作品编号">
                  <Text copyable>{result.work_id}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="作品名称">{result.title}</Descriptions.Item>
                <Descriptions.Item label="总事件数">{result.total_events}</Descriptions.Item>
              </Descriptions>
            </Card>

            {/* 溯源时间线 */}
            <Card title="溯源时间线">
              {result.timeline.length > 0 ? (
                <Timeline
                  items={result.timeline.map((event, i) => {
                    const cfg = eventConfig[event.event_type] || { color: 'gray', icon: null };
                    return {
                      key: i,
                      color: cfg.color,
                      dot: cfg.icon,
                      children: (
                        <div>
                          <Space>
                            <Tag color={cfg.color}>{event.event_name}</Tag>
                            <Text type="secondary">{event.timestamp}</Text>
                          </Space>
                          <div style={{ marginTop: 8 }}>
                            {renderEventDetail(event)}
                          </div>
                        </div>
                      ),
                    };
                  })}
                />
              ) : (
                <Empty description="暂无溯源记录" />
              )}
            </Card>
          </>
        )}

        {!result && !error && !loading && (
          <Card><Empty description="请输入作品编号查询溯源信息" /></Card>
        )}
      </Spin>
    </>
  );
}