/**
 * 文化DNA —— 身份认证申请页
 * 普通用户 / 传承人 / 鉴定师可提交资料，申请认证为另一种身份（传承人 / 鉴定师）。
 */
import { useEffect, useState } from 'react';
import {
  Card, Form, Input, Select, Button, message, Tag, Table, Alert,
} from 'antd';
import { IdcardOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { applyRoleApi, listMyApplicationsApi, RoleApplication } from '../api/certification';
import { getUser } from '../utils/auth';
import PageHeader from '../components/PageHeader';
import { ROLE_LABELS } from '../constants';

const statusMap: Record<string, { color: string; label: string }> = {
  pending: { color: 'orange', label: '待审核' },
  approved: { color: 'success', label: '已通过' },
  rejected: { color: 'error', label: '已驳回' },
};

export default function Certify() {
  const user = getUser();
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const [list, setList] = useState<RoleApplication[]>([]);
  const [loading, setLoading] = useState(false);

  // 可申请的目标身份：排除当前身份（管理员不可自助申请）
  const roleOptions = [
    { value: 'inheritor', label: '传承人' },
    { value: 'appraiser', label: '鉴定师' },
  ].filter((r) => r.value !== user?.role);

  const fetchList = async () => {
    setLoading(true);
    try {
      const res = await listMyApplicationsApi();
      setList(res.items ?? []);
    } catch { /* 拦截器已处理 */ }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchList(); }, []);

  const submit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      await applyRoleApi(values);
      message.success('认证申请已提交，请等待管理员审核');
      form.resetFields();
      fetchList();
    } catch { /* 拦截器已处理 */ }
    finally { setSubmitting(false); }
  };

  const columns: ColumnsType<RoleApplication> = [
    {
      title: '目标身份',
      dataIndex: 'target_role',
      width: 120,
      render: (r: string) => ROLE_LABELS[r] || r,
    },
    { title: '申请时间', dataIndex: 'created_at', width: 180, render: (t: string) => t || '-' },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (s: string) => {
        const m = statusMap[s] || { color: 'default', label: s };
        return <Tag color={m.color}>{m.label}</Tag>;
      },
    },
    { title: '审核意见', dataIndex: 'review_comment', render: (c: string) => c || '-' },
    { title: '审核人', dataIndex: 'reviewer_name', width: 110, render: (n: string) => n || '-' },
  ];

  return (
    <>
      <PageHeader
        title="身份认证"
        subtitle="提交资料申请认证为传承人或鉴定师，管理员审核通过后身份自动生效"
      />

      {roleOptions.length === 0 ? (
        <Alert
          type="info"
          showIcon
          message="您当前无需申请其他身份认证"
          description="如需变更身份请联系管理员处理。"
        />
      ) : (
        <Card
          className="soft-card"
          title="提交认证申请"
          extra={<IdcardOutlined style={{ fontSize: 18, color: '#A8432F' }} />}
          style={{ marginBottom: 20 }}
        >
          <Form
            form={form}
            layout="vertical"
            initialValues={{ real_name: user?.real_name, phone: user?.phone || '' }}
            style={{ maxWidth: 640 }}
          >
            <Form.Item
              name="target_role"
              label="申请身份"
              rules={[{ required: true, message: '请选择要认证的身份' }]}
            >
              <Select placeholder="请选择要认证的身份" options={roleOptions} />
            </Form.Item>
            <Form.Item
              name="real_name"
              label="真实姓名"
              rules={[{ required: true, message: '请输入真实姓名' }]}
            >
              <Input placeholder="请输入真实姓名" />
            </Form.Item>
            <Form.Item name="phone" label="联系电话">
              <Input placeholder="请输入联系电话（选填）" />
            </Form.Item>
            <Form.Item
              name="materials"
              label="申请资料"
              rules={[{ required: true, min: 10, message: '请填写不少于10字的申请资料' }]}
              extra="请填写个人简介、非遗技艺说明、相关资质与传承谱系等证明材料。"
            >
              <Input.TextArea
                rows={5}
                maxLength={500}
                showCount
                placeholder="请填写个人简介、非遗技艺说明、相关资质与传承谱系等证明材料"
              />
            </Form.Item>
          </Form>
          <Button type="primary" loading={submitting} onClick={submit}>提交申请</Button>
        </Card>
      )}

      <Card className="soft-card" title="我的申请记录">
        <Table
          rowKey="id"
          columns={columns}
          dataSource={list}
          loading={loading}
          pagination={false}
          size="middle"
          scroll={{ x: 700 }}
        />
      </Card>
    </>
  );
}