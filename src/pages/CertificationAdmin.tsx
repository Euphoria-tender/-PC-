/**
 * 文化DNA —— 认证管理页（管理员）
 * 审核用户提交的身份认证申请；通过后自动变更申请人角色。
 */
import { useEffect, useState, useCallback } from 'react';
import {
  Table, Button, Modal, Form, Input, Space, Tag, message, Tabs, Descriptions, Typography, Empty,
} from 'antd';
import {
  CheckOutlined, CloseOutlined, ReloadOutlined, SolutionOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { listApplicationsApi, reviewApplicationApi, RoleApplication } from '../api/certification';
import PageHeader from '../components/PageHeader';
import { ROLE_LABELS, ROLE_COLORS } from '../constants';

const { Paragraph } = Typography;

const statusMap: Record<string, { color: string; label: string }> = {
  pending: { color: 'orange', label: '待审核' },
  approved: { color: 'success', label: '已通过' },
  rejected: { color: 'error', label: '已驳回' },
};

export default function CertificationAdmin() {
  const [status, setStatus] = useState<string>('pending');
  const [data, setData] = useState<RoleApplication[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });

  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState<RoleApplication | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listApplicationsApi({
        page: pagination.current,
        page_size: pagination.pageSize,
        status,
      });
      setData(res.items);
      setPagination(prev => ({ ...prev, total: res.pagination?.total ?? 0 }));
    } catch { /* 拦截器已处理 */ }
    finally { setLoading(false); }
  }, [status, pagination.current, pagination.pageSize]);

  useEffect(() => { fetchList(); }, [fetchList]);

  const openModal = (record: RoleApplication) => {
    setCurrent(record);
    form.resetFields();
    setOpen(true);
  };

  const submit = async (result: 'approved' | 'rejected') => {
    if (!current) return;
    const comment = (form.getFieldValue('comment') || '').trim();
    if (result === 'rejected' && !comment) {
      message.error('驳回时请填写审核意见');
      return;
    }
    setSubmitting(true);
    try {
      await reviewApplicationApi(current.id, {
        status: result,
        review_comment: comment || undefined,
      });
      message.success(result === 'approved' ? '已通过，用户身份已更新' : '已驳回');
      setOpen(false);
      fetchList();
    } catch { /* 拦截器已处理 */ }
    finally { setSubmitting(false); }
  };

  const columns: ColumnsType<RoleApplication> = [
    { title: '申请人', dataIndex: 'applicant_username', width: 120 },
    { title: '真实姓名', dataIndex: 'real_name', width: 110 },
    {
      title: '目标身份',
      dataIndex: 'target_role',
      width: 100,
      render: (r: string) => <Tag color={ROLE_COLORS[r] || 'default'}>{ROLE_LABELS[r] || r}</Tag>,
    },
    { title: '联系电话', dataIndex: 'phone', width: 130, render: (p: string) => p || '-' },
    { title: '申请时间', dataIndex: 'created_at', width: 168, render: (t: string) => t || '-' },
    {
      title: '状态',
      dataIndex: 'status',
      width: 96,
      render: (s: string) => {
        const m = statusMap[s] || { color: 'default', label: s };
        return <Tag color={m.color}>{m.label}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 110,
      fixed: 'right',
      render: (_, record) =>
        record.status === 'pending' ? (
          <Button
            type="primary"
            size="small"
            icon={<SolutionOutlined />}
            onClick={() => openModal(record)}
          >
            审核
          </Button>
        ) : (
          <span style={{ color: '#8c8c8c' }}>已处理</span>
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
        title="认证管理"
        subtitle="审核用户提交的身份认证申请，通过后自动变更其角色"
        extra={<Button icon={<ReloadOutlined />} onClick={() => fetchList()}>刷新</Button>}
      />

      <Tabs
        activeKey={status}
        onChange={(k) => { setStatus(k); setPagination(prev => ({ ...prev, current: 1 })); }}
        items={tabItems}
      />

      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        size="middle"
        locale={{ emptyText: <Empty description="暂无申请" /> }}
        pagination={{
          current: pagination.current,
          pageSize: pagination.pageSize,
          total: pagination.total,
          showSizeChanger: true,
          showTotal: t => `共 ${t} 条申请`,
          onChange: (page, pageSize) => setPagination(prev => ({ ...prev, current: page, pageSize })),
        }}
        scroll={{ x: 960 }}
      />

      {/* 审核弹窗 */}
      <Modal
        title="身份认证审核"
        open={open}
        onCancel={() => setOpen(false)}
        footer={[
          <Button key="reject" danger icon={<CloseOutlined />} loading={submitting} onClick={() => submit('rejected')}>
            驳回
          </Button>,
          <Button key="approve" type="primary" icon={<CheckOutlined />} loading={submitting} onClick={() => submit('approved')}>
            通过
          </Button>,
        ]}
        maskClosable={false}
        width={600}
      >
        {current && (
          <Space direction="vertical" style={{ width: '100%' }} size={16}>
            <Descriptions size="small" column={2} bordered>
              <Descriptions.Item label="申请人">{current.applicant_username}</Descriptions.Item>
              <Descriptions.Item label="目标身份">
                <Tag color={ROLE_COLORS[current.target_role] || 'default'}>
                  {ROLE_LABELS[current.target_role] || current.target_role}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="真实姓名">{current.real_name}</Descriptions.Item>
              <Descriptions.Item label="联系电话">{current.phone || '-'}</Descriptions.Item>
              <Descriptions.Item label="申请资料" span={2}>
                <Paragraph style={{ margin: 0 }}>{current.materials}</Paragraph>
              </Descriptions.Item>
            </Descriptions>

            <Form form={form} layout="vertical">
              <Form.Item name="comment" label="审核意见">
                <Input.TextArea
                  rows={3}
                  maxLength={500}
                  showCount
                  placeholder="驳回时请填写理由（通过时可选）"
                />
              </Form.Item>
            </Form>
          </Space>
        )}
      </Modal>
    </>
  );
}