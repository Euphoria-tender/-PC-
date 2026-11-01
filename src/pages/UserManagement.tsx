/**
 * 文化DNA —— 用户管理页（管理员）
 */
import { useState, useEffect, useCallback } from 'react';
import {
  Table, Button, Modal, Form, Input, Select, Popconfirm, Space, Tag, message, Tooltip,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, KeyOutlined } from '@ant-design/icons';
import {
  listUsersApi, createUserApi, updateUserApi, deleteUserApi, resetUserPasswordApi,
  UserItem, PaginatedResult,
} from '../api/admin';
import PageHeader from '../components/PageHeader';
import { ROLE_LABELS, ROLE_COLORS } from '../constants';

export default function UserManagement() {
  const [data, setData] = useState<PaginatedResult<UserItem> | null>(null);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState('');
  const [roleFilter, setRoleFilter] = useState<string | undefined>(undefined);

  // 创建/编辑弹窗
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [editUser, setEditUser] = useState<UserItem | null>(null);
  const [submitLoading, setSubmitLoading] = useState(false);
  const [form] = Form.useForm();

  // 重置密码弹窗
  const [pwdModalOpen, setPwdModalOpen] = useState(false);
  const [pwdUserId, setPwdUserId] = useState<number | null>(null);
  const [pwdLoading, setPwdLoading] = useState(false);
  const [pwdForm] = Form.useForm();

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listUsersApi({ page, page_size: 20, keyword, role: roleFilter });
      setData(res);
    } catch {
      // 错误在拦截器中处理
    } finally {
      setLoading(false);
    }
  }, [page, keyword, roleFilter]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  /** 打开创建弹窗 */
  const openCreate = () => {
    setModalMode('create');
    setEditUser(null);
    form.resetFields();
    setModalOpen(true);
  };

  /** 打开编辑弹窗 */
  const openEdit = (user: UserItem) => {
    setModalMode('edit');
    setEditUser(user);
    form.setFieldsValue({
      real_name: user.real_name,
      phone: user.phone,
      role: user.role,
    });
    setModalOpen(true);
  };

  /** 提交创建/编辑 */
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitLoading(true);
      if (modalMode === 'create') {
        await createUserApi(values);
        message.success('用户创建成功');
      } else if (editUser) {
        await updateUserApi(editUser.id, values);
        message.success('用户信息更新成功');
      }
      setModalOpen(false);
      fetchUsers();
    } catch {
      // 验证错误在表单中显示
    } finally {
      setSubmitLoading(false);
    }
  };

  /** 删除用户 */
  const handleDelete = async (user: UserItem) => {
    try {
      await deleteUserApi(user.id);
      message.success('用户已删除');
      fetchUsers();
    } catch {
      // 错误在拦截器中处理
    }
  };

  /** 重置密码 */
  const handleResetPwd = async () => {
    try {
      const values = await pwdForm.validateFields();
      setPwdLoading(true);
      await resetUserPasswordApi(pwdUserId!, values.new_password);
      message.success('密码重置成功');
      setPwdModalOpen(false);
      pwdForm.resetFields();
    } catch {
      // 错误在拦截器中处理
    } finally {
      setPwdLoading(false);
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '用户名', dataIndex: 'username', width: 120 },
    { title: '真实姓名', dataIndex: 'real_name', width: 120 },
    {
      title: '角色',
      dataIndex: 'role',
      width: 100,
      render: (role: string) => {
        const info = ROLE_LABELS[role];
        return <Tag color={ROLE_COLORS[role] || 'default'}>{info || role}</Tag>;
      },
    },
    { title: '手机号', dataIndex: 'phone', width: 130 },
    {
      title: '微信绑定',
      dataIndex: 'openid',
      width: 100,
      render: (v: string) => v ? <Tag color="green">已绑定</Tag> : <Tag>未绑定</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 170,
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: UserItem) => {
        const isLastAdmin = record.role === 'admin' && (data?.total_admins ?? 0) <= 1;
        return (
          <Space size="small">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => openEdit(record)}
            >
              编辑
            </Button>
            <Button
              type="link"
              size="small"
              icon={<KeyOutlined />}
              onClick={() => {
                setPwdUserId(record.id);
                pwdForm.resetFields();
                setPwdModalOpen(true);
              }}
            >
              重置密码
            </Button>
            {isLastAdmin ? (
              <Tooltip title="系统至少保留一个管理员账号">
                <Button type="link" size="small" danger disabled icon={<DeleteOutlined />}>
                  删除
                </Button>
              </Tooltip>
            ) : (
              <Popconfirm
                title="确定删除该用户吗？"
                onConfirm={() => handleDelete(record)}
                okText="确定"
                cancelText="取消"
              >
                <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                  删除
                </Button>
              </Popconfirm>
            )}
          </Space>
        );
      },
    },
  ];

  return (
    <div>
      <PageHeader
        title="用户管理"
        subtitle="账号、角色与密码管理（系统始终保留至少一名管理员）"
      />

      {/* 工具栏 */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Space>
          <Input.Search
            placeholder="搜索用户名/姓名"
            allowClear
            onSearch={(v) => { setKeyword(v); setPage(1); }}
            style={{ width: 220 }}
          />
          <Select
            placeholder="角色筛选"
            allowClear
            style={{ width: 120 }}
            value={roleFilter}
            onChange={(v) => { setRoleFilter(v); setPage(1); }}
            options={Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }))}
          />
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          创建用户
        </Button>
      </div>

      {/* 表格 */}
      <Table
        columns={columns}
        dataSource={data?.items || []}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize: 20,
          total: data?.pagination?.total || 0,
          onChange: setPage,
          showTotal: (total) => `共 ${total} 条`,
          showSizeChanger: false,
        }}
        scroll={{ x: 1000 }}
      />

      {/* 创建/编辑弹窗 */}
      <Modal
        title={modalMode === 'create' ? '创建用户' : '编辑用户'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={submitLoading}
        destroyOnClose
      >
        <Form form={form} layout="vertical" autoComplete="off">
          {modalMode === 'create' && (
            <>
              <Form.Item
                name="username"
                label="用户名"
                rules={[
                  { required: true, message: '请输入用户名' },
                  { min: 3, message: '至少3个字符' },
                ]}
              >
                <Input placeholder="用户名" />
              </Form.Item>
              <Form.Item
                name="password"
                label="密码"
                rules={[
                  { required: true, message: '请输入密码' },
                  { min: 6, message: '至少6个字符' },
                ]}
              >
                <Input.Password placeholder="密码" />
              </Form.Item>
            </>
          )}
          <Form.Item
            name="real_name"
            label="真实姓名"
            rules={[{ required: true, message: '请输入真实姓名' }]}
          >
            <Input placeholder="真实姓名" />
          </Form.Item>
          <Form.Item name="phone" label="手机号">
            <Input placeholder="手机号" />
          </Form.Item>
          <Form.Item
            name="role"
            label="角色"
            rules={[{ required: true, message: '请选择角色' }]}
          >
            <Select
              options={Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }))}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 重置密码弹窗 */}
      <Modal
        title="重置密码"
        open={pwdModalOpen}
        onOk={handleResetPwd}
        onCancel={() => setPwdModalOpen(false)}
        confirmLoading={pwdLoading}
        destroyOnClose
      >
        <Form form={pwdForm} layout="vertical">
          <Form.Item
            name="new_password"
            label="新密码"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '至少6个字符' },
            ]}
          >
            <Input.Password placeholder="新密码" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}