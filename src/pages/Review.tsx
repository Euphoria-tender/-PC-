/**
 * 文化DNA —— 专家审核页
 * 鉴定师 / 管理员对待审核作品进行专业审核，并给出评级（大师级/精品级/优良级/合格级）。
 * 普通用户与传承人无此入口（ROLE_ACCESS 中仅 admin、appraiser 含 /review）。
 */
import { useEffect, useState, useCallback } from 'react';
import {
  Table, Button, Modal, Form, Select, Input, Space, Tag, message,
  Typography, Tabs, Image, Descriptions, Empty,
} from 'antd';
import {
  SafetyCertificateOutlined,
  CheckOutlined,
  CloseOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { listArtworksForReviewApi, reviewArtworkApi, ArtworkReviewItem } from '../api/admin';
import PageHeader from '../components/PageHeader';
import { imgUrl } from '../utils/host';
import { GRADE_OPTIONS, GRADE_LABELS, GRADE_COLORS } from '../constants';

const { Text, Paragraph } = Typography;

const dnaStatusMap: Record<string, { color: string; label: string }> = {
  pending: { color: 'default', label: '待提取' },
  processing: { color: 'processing', label: '提取中' },
  completed: { color: 'success', label: '已提取' },
  failed: { color: 'error', label: '提取失败' },
};

const reviewStatusMap: Record<string, { color: string; label: string }> = {
  pending: { color: 'orange', label: '待审核' },
  approved: { color: 'success', label: '已通过' },
  rejected: { color: 'error', label: '已驳回' },
};

export default function Review() {
  const [status, setStatus] = useState<string>('pending');
  const [data, setData] = useState<ArtworkReviewItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });

  const [reviewOpen, setReviewOpen] = useState(false);
  const [current, setCurrent] = useState<ArtworkReviewItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listArtworksForReviewApi({
        page: pagination.current,
        page_size: pagination.pageSize,
        review_status: status,
      });
      setData(res.items);
      setPagination(prev => ({ ...prev, total: res.pagination?.total ?? 0 }));
    } catch { /* 拦截器已处理 */ }
    finally { setLoading(false); }
  }, [status, pagination.current, pagination.pageSize]);

  useEffect(() => { fetchList(); }, [fetchList]);

  const openReview = (record: ArtworkReviewItem) => {
    setCurrent(record);
    form.resetFields();
    setReviewOpen(true);
  };

  const submit = async (result: 'approved' | 'rejected') => {
    if (!current) return;

    let grade: string | undefined;
    let comment = '';

    if (result === 'approved') {
      const v = await form.validateFields(['grade']).catch(() => null);
      if (!v) return;
      grade = v.grade;
      comment = (form.getFieldValue('comment') || '').trim();
    } else {
      comment = (form.getFieldValue('comment') || '').trim();
      if (!comment) {
        message.error('驳回时请填写审核意见');
        return;
      }
    }

    setSubmitting(true);
    try {
      await reviewArtworkApi(current.work_id, {
        review_status: result,
        review_comment: comment || undefined,
        review_grade: grade,
      });
      message.success(result === 'approved' ? `已通过并评级 · ${GRADE_LABELS[grade!]}` : '已驳回');
      setReviewOpen(false);
      fetchList();
    } catch { /* 拦截器已处理 */ }
    finally { setSubmitting(false); }
  };

  const columns: ColumnsType<ArtworkReviewItem> = [
    {
      title: '作品图片',
      dataIndex: 'images',
      key: 'images',
      width: 72,
      render: (imgs: string[]) =>
        imgs?.[0] ? (
          <Image
            src={imgUrl(imgs[0])}
            width={48}
            height={48}
            style={{ objectFit: 'cover', borderRadius: 4 }}
          />
        ) : (
          <div
            style={{
              width: 48, height: 48, borderRadius: 4, background: '#f0ede4',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#b9b29f', fontSize: 12,
            }}
          >
            无图
          </div>
        ),
    },
    {
      title: '作品编号',
      dataIndex: 'work_id',
      key: 'work_id',
      width: 110,
      ellipsis: true,
      render: (id: string) => <Text copyable style={{ fontSize: 12 }}>{id.slice(0, 8)}…</Text>,
    },
    { title: '作品名称', dataIndex: 'title', key: 'title', width: 170, ellipsis: true },
    { title: '类别', dataIndex: 'category', key: 'category', width: 80 },
    { title: '传承人', dataIndex: 'owner_name', key: 'owner_name', width: 100 },
    {
      title: 'DNA状态',
      dataIndex: 'dna_status',
      key: 'dna_status',
      width: 96,
      render: (s: string) => {
        const m = dnaStatusMap[s] || { color: 'default', label: s };
        return <Tag color={m.color}>{m.label}</Tag>;
      },
    },
    {
      title: '审核状态',
      dataIndex: 'review_status',
      key: 'review_status',
      width: 96,
      render: (s: string) => {
        const m = reviewStatusMap[s] || { color: 'default', label: s };
        return <Tag color={m.color}>{m.label}</Tag>;
      },
    },
    {
      title: '专家评级',
      dataIndex: 'review_grade',
      key: 'review_grade',
      width: 100,
      render: (g: string) =>
        g ? <Tag color={GRADE_COLORS[g] || 'default'}>{GRADE_LABELS[g] || g}</Tag> : '-',
    },
    {
      title: '审核人',
      dataIndex: 'reviewer_name',
      key: 'reviewer_name',
      width: 96,
      render: (n: string) => n || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 168,
      render: (t: string) => t || '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 110,
      fixed: 'right',
      render: (_, record) => (
        <Button
          type="primary"
          size="small"
          icon={<SafetyCertificateOutlined />}
          onClick={() => openReview(record)}
        >
          {record.review_status === 'pending' ? '审核' : '重审'}
        </Button>
      ),
    },
  ];

  const tabItems = [
    { key: 'pending', label: '待审核' },
    { key: 'approved', label: '已通过' },
    { key: 'rejected', label: '已驳回' },
  ];

  return (
    <>
      <PageHeader
        title="专家审核"
        subtitle="对待审核作品进行专业鉴定并给出评级"
        extra={<Button icon={<ReloadOutlined />} onClick={() => fetchList()}>刷新</Button>}
      />

      <Tabs
        activeKey={status}
        onChange={(k) => { setStatus(k); setPagination(prev => ({ ...prev, current: 1 })); }}
        items={tabItems}
      />

      <Table
        rowKey="work_id"
        columns={columns}
        dataSource={data}
        loading={loading}
        size="middle"
        locale={{ emptyText: <Empty description="暂无数据" /> }}
        pagination={{
          current: pagination.current,
          pageSize: pagination.pageSize,
          total: pagination.total,
          showSizeChanger: true,
          showTotal: t => `共 ${t} 件`,
          onChange: (page, pageSize) => setPagination(prev => ({ ...prev, current: page, pageSize })),
        }}
        scroll={{ x: 1150 }}
      />

      {/* 审核弹窗 */}
      <Modal
        title={
          <span>
            作品审核
            <Tag color="orange" style={{ marginLeft: 8 }}>{current?.work_id.slice(0, 8)}…</Tag>
          </span>
        }
        open={reviewOpen}
        onCancel={() => setReviewOpen(false)}
        footer={[
          <Button key="reject" danger icon={<CloseOutlined />} loading={submitting} onClick={() => submit('rejected')}>
            驳回
          </Button>,
          <Button key="approve" type="primary" icon={<CheckOutlined />} loading={submitting} onClick={() => submit('approved')}>
            通过并评级
          </Button>,
        ]}
        maskClosable={false}
        width={640}
      >
        {current && (
          <Space direction="vertical" style={{ width: '100%' }} size={16}>
            <Descriptions size="small" column={2} bordered>
              <Descriptions.Item label="作品名称" span={2}>{current.title}</Descriptions.Item>
              <Descriptions.Item label="类别">{current.category}</Descriptions.Item>
              <Descriptions.Item label="传承人">{current.owner_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="DNA 状态">
                {dnaStatusMap[current.dna_status]?.label || current.dna_status}
              </Descriptions.Item>
              <Descriptions.Item label="当前状态">
                <Tag color={reviewStatusMap[current.review_status]?.color}>
                  {reviewStatusMap[current.review_status]?.label}
                </Tag>
              </Descriptions.Item>
              {current.description && (
                <Descriptions.Item label="作品描述" span={2}>
                  <Paragraph style={{ margin: 0 }}>{current.description}</Paragraph>
                </Descriptions.Item>
              )}
            </Descriptions>

            {current.images?.length ? (
              <Image.PreviewGroup>
                <Space wrap>
                  {current.images.map((p, i) => (
                    <Image
                      key={i}
                      src={imgUrl(p)}
                      width={88}
                      height={88}
                      style={{ objectFit: 'cover', borderRadius: 6 }}
                    />
                  ))}
                </Space>
              </Image.PreviewGroup>
            ) : null}

            <Form form={form} layout="vertical">
              <Form.Item
                name="grade"
                label="专家评级"
                rules={[{ required: true, message: '请选择评级档位' }]}
                extra="通过时必须给出评级；评级将记录在存证与鉴定结论中。"
              >
                <Select
                  placeholder="请选择评级（大师级 / 精品级 / 优良级 / 合格级）"
                  options={GRADE_OPTIONS}
                  allowClear
                />
              </Form.Item>
              <Form.Item name="comment" label="审核意见">
                <Input.TextArea
                  rows={3}
                  maxLength={500}
                  showCount
                  placeholder="驳回时请填写不符合要求的具体理由（通过时可选）"
                />
              </Form.Item>
            </Form>
          </Space>
        )}
      </Modal>
    </>
  );
}