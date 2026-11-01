/**
 * 文化DNA —— 证书验证页
 * 输入证书编号，验证存证信息真伪
 */
import { useState } from 'react';
import {
  Card, Input, Button, Typography, Descriptions, Tag, Result,
  Space, Spin, message, Timeline,
} from 'antd';
import {
  SafetyCertificateOutlined, SearchOutlined,
  CheckCircleOutlined, CloseCircleOutlined,
  LinkOutlined, ClockCircleOutlined,
} from '@ant-design/icons';
import { verifyCertificateApi } from '../api/certificates';
import PageHeader from '../components/PageHeader';
import { palette } from '../theme';

const { Text, Paragraph } = Typography;

export default function Verify() {
  const [certNo, setCertNo] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const handleVerify = async () => {
    const trimmed = certNo.trim();
    if (!trimmed) {
      message.warning('请输入证书编号');
      return;
    }

    setLoading(true);
    setResult(null);
    setError('');

    try {
      const data: any = await verifyCertificateApi(trimmed);
      setResult(data);
      if (data.is_valid) {
        message.success('证书验证通过！');
      } else {
        message.warning('证书验证未通过');
      }
    } catch (err: any) {
      setError(err?.message || '验证失败');
      message.error('证书验证失败，请检查编号是否正确');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <PageHeader title="证书验证" subtitle="在区块链上验证存证证书编号的真实性" />

      {/* 证书编号输入 */}
      <Card className="soft-card" style={{ marginBottom: 24 }}>
        <Space.Compact style={{ width: '100%' }}>
          <Input
            size="large"
            placeholder="请输入证书编号，如：CERT-XXXXXXXXXXXX"
            value={certNo}
            onChange={(e) => setCertNo(e.target.value)}
            onPressEnter={handleVerify}
            prefix={<SafetyCertificateOutlined />}
          />
          <Button
            type="primary"
            size="large"
            icon={<SearchOutlined />}
            onClick={handleVerify}
            loading={loading}
          >
            验证
          </Button>
        </Space.Compact>
      </Card>

      {/* 加载状态 */}
      {loading && (
        <Card className="soft-card" style={{ textAlign: 'center', padding: 48 }}>
          <Spin size="large" />
          <Paragraph style={{ marginTop: 16 }}>
            <Text type="secondary">正在区块链上验证存证记录...</Text>
          </Paragraph>
        </Card>
      )}

      {/* 错误 */}
      {error && !loading && (
        <Card className="soft-card">
          <Result
            status="error"
            title="验证失败"
            subTitle={error}
          />
        </Card>
      )}

      {/* 验证结果 */}
      {result && !loading && (
        <>
          <Card className="soft-card" style={{ marginBottom: 16 }}>
            <Result
              status={result.is_valid ? 'success' : 'warning'}
              title={result.is_valid ? '证书验证通过' : '证书验证未通过'}
              icon={result.is_valid
                ? <CheckCircleOutlined style={{ color: palette.success }} />
                : <CloseCircleOutlined style={{ color: palette.warning }} />
              }
            />
          </Card>

          {/* 数据库记录 */}
          {result.db_record && (
            <Card className="soft-card" title="存证记录" style={{ marginBottom: 16 }}>
              <Descriptions bordered column={2}>
                <Descriptions.Item label="证书编号">
                  <Text code>{result.db_record.certificate_no}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Tag color={result.db_record.status === 'success' ? 'success' : 'error'}>
                    {result.db_record.status === 'success' ? '存证成功' : result.db_record.status}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="交易 ID">
                  <Text code style={{ fontSize: 12 }}>{result.db_record.tx_id || '-'}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="区块高度">
                  {result.db_record.block_height || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="链码">
                  {result.db_record.chain_code || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="通道">
                  {result.db_record.channel_name || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="创建时间" span={2}>
                  {result.db_record.created_at || '-'}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          )}

          {/* 区块链记录 */}
          {result.chain_record && (
            <Card className="soft-card" title="区块链记录" style={{ marginBottom: 16 }}>
              <Descriptions bordered column={1}>
                <Descriptions.Item label="链上交易ID">
                  <Text code>{result.chain_record.tx_id || '-'}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="区块高度">
                  <Text code style={{ fontSize: 12 }}>{result.chain_record.block_height || '-'}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="时间戳">
                  {result.chain_record.timestamp || '-'}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          )}

          {/* 关联作品信息 */}
          {result.work_info && (
            <Card className="soft-card" title="关联作品">
              <Descriptions bordered column={2}>
                <Descriptions.Item label="作品名称">{result.work_info.title}</Descriptions.Item>
                <Descriptions.Item label="分类">
                  <Tag>{result.work_info.category}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="DNA 哈希" span={2}>
                  <Text code style={{ fontSize: 12 }}>{result.work_info.dna_hash}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="作者">{result.work_info.owner_name}</Descriptions.Item>
                <Descriptions.Item label="存证时间">{result.work_info.created_at}</Descriptions.Item>
              </Descriptions>
            </Card>
          )}
        </>
      )}
    </div>
  );
}