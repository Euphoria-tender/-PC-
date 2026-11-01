/**
 * 文化DNA —— AI 鉴定页（本地指纹识别 + 联网交叉比对）
 */
import { useState } from 'react';
import {
  Card, Upload, Button, Space, Typography, List, Tag, Image,
  Descriptions, Spin, message, Divider, Empty, Statistic,
  Switch, Alert, Tooltip, Input,
} from 'antd';
import {
  CameraOutlined, SearchOutlined,
  TrophyOutlined, InboxOutlined,
  GlobalOutlined, LinkOutlined,
} from '@ant-design/icons';
import type { UploadFile } from 'antd';
import {
  identifyApi, identifyOnlineApi,
  IdentifyMatch, IdentifyResponse, IdentifyOnlineResponse,
} from '../api/identify';
import PageHeader from '../components/PageHeader';
import { similarityColor, percent } from '../utils/format';
import { imgUrl } from '../utils/host';
import { palette } from '../theme';

const { Text, Paragraph } = Typography;
const { Dragger } = Upload;

const FALLBACK_IMG =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';

export default function Identify() {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<IdentifyResponse | null>(null);
  const [onlineMode, setOnlineMode] = useState(false);
  const [onlineResult, setOnlineResult] = useState<IdentifyOnlineResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  /** 执行识别 */
  const handleIdentify = async () => {
    if (fileList.length === 0) {
      message.warning('请先上传或拍摄一张图片');
      return;
    }

    const file = fileList[0].originFileObj;
    if (!file) {
      message.warning('无法获取文件');
      return;
    }

    setLoading(true);
    setResult(null);
    setOnlineResult(null);

    try {
      if (onlineMode) {
        const query = searchQuery.trim() || undefined;
        const data = await identifyOnlineApi(file, 10, query);
        setOnlineResult(data);
        setResult(data.local);
        if (data.online.available && data.online.results.length > 0) {
          message.success(`本地 ${data.local.matches.length} 个匹配 · 联网参考 ${data.online.results.length} 个（${data.response_time_ms}ms）`);
        } else {
          message.info('联网比对无参考结果，已降级为仅本地识别');
        }
      } else {
        const data = await identifyApi(file, 10);
        setResult(data);
        if (data.matches.length === 0) {
          message.info('未找到匹配的作品，请尝试不同角度或光线拍摄');
        } else {
          message.success(`识别完成，找到 ${data.matches.length} 个匹配（${data.response_time_ms}ms）`);
        }
      }
    } catch {
      message.error('识别失败，请检查后端服务是否运行');
    } finally {
      setLoading(false);
    }
  };

  /** 文件上传前校验 + 预览 */
  const handleBeforeUpload = (file: File) => {
    if (!file.type.startsWith('image/')) {
      message.error('只能上传图片文件！');
      return false;
    }
    if (file.size / 1024 / 1024 >= 10) {
      message.error('图片大小不能超过 10MB！');
      return false;
    }
    setFileList([{ uid: '-1', name: file.name, status: 'done', originFileObj: file as any }]);
    setResult(null);
    setOnlineResult(null);
    return false; // 阻止自动上传，由我们手动处理
  };

  /** 匹配结果标签 */
  const getMatchTag = (isMatch: boolean, score: number) => {
    if (isMatch && score >= 0.95) return <Tag color="success">高度匹配</Tag>;
    if (isMatch) return <Tag color="processing">匹配</Tag>;
    if (score >= 0.7) return <Tag color="warning">相似</Tag>;
    return <Tag color="default">低相似度</Tag>;
  };

  /** 联网鉴定 · 综合结论 */
  const renderVerdict = () => {
    if (!onlineMode || !onlineResult || !onlineResult.online.available || !result || result.matches.length === 0) {
      return null;
    }
    const localTop = result.matches[0].similarity;
    const onlineMax = Math.max(...onlineResult.online.results.map((r) => r.similarity));

    let type: 'success' | 'warning' | 'info' = 'info';
    let title = '';
    let desc = '';

    if (localTop >= 0.95 && onlineMax >= 0.7) {
      type = 'success';
      title = '鉴定可信度高';
      desc = `本地指纹强匹配（${percent(localTop)}），且联网参考存在 ${percent(onlineMax)} 的交叉相似佐证，判定为同一作品的可信度较高。`;
    } else if (localTop >= 0.95) {
      type = 'warning';
      title = '本地强匹配，联网佐证不足';
      desc = `本地库中命中同一作品（${percent(localTop)}），但联网未找到高度相似参考，建议核对来源与存证信息。`;
    } else if (onlineMax >= 0.85) {
      type = 'info';
      title = '联网发现疑似同源参考';
      desc = `本地匹配度有限，但联网交叉比对最高 ${percent(onlineMax)}，可能与某一网络参考作品同源，建议人工复核。`;
    } else {
      type = 'info';
      title = '暂未形成明确结论';
      desc = '本地与联网均未形成强匹配，可能为未收录作品，建议补充更多角度图片或联系鉴定师。';
    }

    return (
      <Alert type={type} showIcon message={title} description={desc} style={{ marginBottom: 16 }} />
    );
  };

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <PageHeader
        title="AI 鉴定"
        subtitle="上传非遗作品图片，提取视觉特征并与本地指纹库比对；开启联网后交叉比对网络参考，形成鉴定结论。"
      />

      {/* 上传区域 */}
      <Card title="上传待识别图片" className="soft-card" style={{ marginBottom: 16 }}>
        <Dragger
          name="identify_image"
          multiple={false}
          beforeUpload={handleBeforeUpload}
          onRemove={() => {
            setFileList([]);
            setResult(null);
            setOnlineResult(null);
          }}
          fileList={fileList}
          accept="image/png,image/jpeg,image/jpg,image/webp"
          showUploadList={{ showPreviewIcon: true, showRemoveIcon: true }}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽图片到此区域</p>
          <p className="ant-upload-hint">支持 PNG、JPG、JPEG、WEBP 格式，大小不超过 10MB</p>
        </Dragger>

        {/* 联网鉴定开关 + 关键词 */}
        <div
          style={{
            marginTop: 16,
            padding: '12px 16px',
            background: palette.paper,
            borderRadius: 10,
            border: `1px solid ${palette.borderLight}`,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
            <Tooltip title="开启后在本地识别结果之上，联网搜索参考作品并进行交叉比对相似度">
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <GlobalOutlined style={{ color: palette.celadon }} />
                <Text>联网鉴定</Text>
                <Switch
                  checked={onlineMode}
                  onChange={setOnlineMode}
                  checkedChildren="本地 + 联网"
                  unCheckedChildren="仅本地"
                />
              </span>
            </Tooltip>
          </div>
          {onlineMode && (
            <Input
              allowClear
              style={{ marginTop: 12 }}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="可选：输入作品名称或工艺关键词，提升联网搜索准确性（如「青花 瓷」；留空则自动推断）"
              prefix={<SearchOutlined style={{ color: palette.inkTertiary }} />}
              maxLength={60}
            />
          )}
        </div>

        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Space size="large">
            <Button
              type="primary"
              size="large"
              icon={<SearchOutlined />}
              onClick={handleIdentify}
              loading={loading}
              disabled={fileList.length === 0}
            >
              开始鉴定
            </Button>
            <Button
              size="large"
              icon={<CameraOutlined />}
              onClick={() => {
                const input = document.createElement('input');
                input.type = 'file';
                input.accept = 'image/*';
                input.capture = 'environment';
                input.onchange = (e) => {
                  const file = (e.target as HTMLInputElement).files?.[0];
                  if (file) handleBeforeUpload(file);
                };
                input.click();
              }}
            >
              拍照识别
            </Button>
          </Space>
        </div>
      </Card>

      {/* 加载状态 */}
      {loading && (
        <Card className="soft-card" style={{ textAlign: 'center', padding: 48 }}>
          <Spin size="large" />
          <Paragraph style={{ marginTop: 16, marginBottom: 0 }}>
            <Text type="secondary">
              {onlineMode ? '正在提取特征 · 检索本地库 · 联网搜索并交叉比对…' : '正在提取特征并比对数据库…'}
            </Text>
          </Paragraph>
        </Card>
      )}

      {/* 无结果 */}
      {!loading && result && result.matches.length === 0 && (
        <Card className="soft-card">
          <Empty description="未找到匹配的作品" />
        </Card>
      )}

      {/* 匹配结果 */}
      {!loading && result && result.matches.length > 0 && (
        <>
          <Card className="soft-card" style={{ marginBottom: 16 }}>
            <Space size="large" wrap>
              <Statistic title="匹配数量" value={result.matches.length} suffix={`/ ${result.total_in_database} 件作品`} />
              <Statistic title="响应时间" value={result.response_time_ms} suffix="ms" />
              <Statistic
                title="最佳匹配"
                value={percent(result.matches[0].similarity)}
                valueStyle={{ color: similarityColor(result.matches[0].similarity) }}
              />
            </Space>
          </Card>

          <Card title="本地识别结果" className="soft-card">
            <List
              dataSource={result.matches}
              renderItem={(item: IdentifyMatch, index: number) => (
                <List.Item
                  key={item.work_id}
                  style={{
                    background: index === 0 ? palette.cinnabarLight : undefined,
                    borderRadius: 8,
                    padding: 16,
                    marginBottom: 8,
                  }}
                >
                  <div style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <Space size={8}>
                        {index === 0 && <TrophyOutlined style={{ color: palette.gold }} />}
                        <Text strong style={{ fontSize: 16 }}>{item.title}</Text>
                        {getMatchTag(item.is_match, item.similarity)}
                        <Tag>{item.category}</Tag>
                      </Space>
                      <Text strong style={{ fontSize: 20, color: similarityColor(item.similarity) }}>
                        {percent(item.similarity)}
                      </Text>
                    </div>

                    <Descriptions size="small" column={3}>
                      <Descriptions.Item label="作者">{item.owner_name || '未知'}</Descriptions.Item>
                      <Descriptions.Item label="DNA哈希">
                        <Text code style={{ fontSize: 12 }}>{item.dna_hash?.substring(0, 16)}…</Text>
                      </Descriptions.Item>
                      <Descriptions.Item label="作品编号">
                        <Text code>{item.work_id?.substring(0, 8)}…</Text>
                      </Descriptions.Item>
                    </Descriptions>

                    {item.description && (
                      <Paragraph type="secondary" ellipsis={{ rows: 2 }} style={{ marginTop: 8, marginBottom: 0 }}>
                        {item.description}
                      </Paragraph>
                    )}

                    {item.images && item.images.length > 0 && (
                      <div style={{ marginTop: 8 }}>
                        <Image.PreviewGroup>
                          {item.images.slice(0, 3).map((img, i) => (
                            <Image
                              key={i}
                              src={imgUrl(img)}
                              width={60}
                              height={60}
                              style={{ objectFit: 'cover', marginRight: 8, borderRadius: 4 }}
                              fallback={FALLBACK_IMG}
                            />
                          ))}
                        </Image.PreviewGroup>
                      </div>
                    )}
                  </div>
                </List.Item>
              )}
            />
          </Card>
        </>
      )}

      {/* 联网比对结果（双向识别） */}
      {!loading && onlineMode && onlineResult && (
        <>
          <Divider plain style={{ marginTop: 24 }}>
            <GlobalOutlined /> 联网交叉比对
          </Divider>

          {renderVerdict()}

          {onlineResult.online.available && onlineResult.online.results.length > 0 ? (
            <>
              <Card className="soft-card" style={{ marginBottom: 16 }}>
                <Space size="large" wrap>
                  <Statistic title="搜索关键词" value={onlineResult.online.query || '—'} />
                  <Statistic title="联网参考数" value={onlineResult.online.results.length} suffix="件" />
                  <Statistic
                    title="最高交叉相似度"
                    value={percent(Math.max(...onlineResult.online.results.map((r) => r.similarity)))}
                    valueStyle={{ color: similarityColor(Math.max(...onlineResult.online.results.map((r) => r.similarity))) }}
                  />
                </Space>
              </Card>

              <Card title="参考作品（上传图 ↔ 联网图 交叉比对）" className="soft-card">
                <List
                  dataSource={onlineResult.online.results}
                  renderItem={(item) => (
                    <List.Item
                      style={{ padding: 16, marginBottom: 8, border: `1px solid ${palette.borderLight}`, borderRadius: 8 }}
                    >
                      <div style={{ width: '100%', display: 'flex', gap: 16 }}>
                        <Image
                          src={imgUrl(item.image_url)}
                          width={100}
                          height={100}
                          style={{ objectFit: 'cover', borderRadius: 6, flexShrink: 0 }}
                          fallback={FALLBACK_IMG}
                        />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <Text strong style={{ fontSize: 15 }}>{item.title || '未命名参考图'}</Text>
                          <div style={{ marginTop: 4 }}>
                            <Tag>上传图 ↔ 联网图</Tag>
                            <Text strong style={{ fontSize: 20, color: similarityColor(item.similarity) }}>
                              {percent(item.similarity)}
                            </Text>
                          </div>
                          <div style={{ marginTop: 8 }}>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              CNN {percent(item.cnn_similarity)} · 感知哈希 {percent(item.dhash_similarity)}
                            </Text>
                          </div>
                          {item.source_url && (
                            <Paragraph type="secondary" ellipsis style={{ marginTop: 6, marginBottom: 0, fontSize: 12 }}>
                              <LinkOutlined /> 来源：
                              <a href={item.source_url} target="_blank" rel="noreferrer">
                                {item.source_url}
                              </a>
                            </Paragraph>
                          )}
                        </div>
                      </div>
                    </List.Item>
                  )}
                />
              </Card>
            </>
          ) : (
            <Alert
              type="info"
              showIcon
              message="联网比对不可用"
              description="未获取到联网参考作品（可能网络不通或搜索无结果），已降级为仅本地识别。"
              style={{ marginBottom: 16 }}
            />
          )}
        </>
      )}
    </div>
  );
}