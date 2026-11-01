/**
 * 文化DNA —— 作品管理页
 * 表格列表 + 新增Modal + 上传显微图像 + 提取DNA + 上链存证
 */
import { useEffect, useState, useCallback } from 'react';
import {
  Table, Button, Modal, Form, Input, Select, Upload, Space, Tag, message,
  Popconfirm, Typography, Card,
} from 'antd';
import {
  PlusOutlined, UploadOutlined, ScanOutlined, SafetyCertificateOutlined,
  DeleteOutlined, ReloadOutlined, SearchOutlined, InboxOutlined,
  CloudServerOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { UploadFile } from 'antd/es/upload';
import {
  listWorksApi, createWorkApi, deleteWorkApi, extractDnaApi, uploadMicroscopeApi,
  WorkItem, WorkListParams,
} from '../api/works';
import { createCertificateApi } from '../api/certificates';
import { publishWorkApi } from '../api/publish';
import PageHeader from '../components/PageHeader';
import { CATEGORIES } from '../constants';

const { Text } = Typography;
const { Dragger } = Upload;

/** DNA 状态映射 */
const dnaStatusMap: Record<string, { color: string; label: string }> = {
  pending: { color: 'default', label: '待提取' },
  processing: { color: 'processing', label: '提取中' },
  completed: { color: 'success', label: '已提取' },
  failed: { color: 'error', label: '提取失败' },
};


export default function Works() {
  // ── 列表状态 ─────────────────────────────────────────────────
  const [data, setData] = useState<WorkItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 12, total: 0 });
  const [filters, setFilters] = useState<WorkListParams>({});

  // ── 弹窗状态 ─────────────────────────────────────────────────
  const [createOpen, setCreateOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [createForm] = Form.useForm();

  const [microOpen, setMicroOpen] = useState(false);
  const [microWorkId, setMicroWorkId] = useState('');
  const [microFiles, setMicroFiles] = useState<UploadFile[]>([]);
  const [microUploading, setMicroUploading] = useState(false);

  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // ── 加载列表 ─────────────────────────────────────────────────
  const fetchList = useCallback(async (params?: WorkListParams) => {
    setLoading(true);
    try {
      const query = { ...filters, ...params, page: pagination.current, page_size: pagination.pageSize };
      const res = await listWorksApi(query) as any;
      const items = res?.items ?? [];
      const p = res?.pagination ?? {};
      setData(items);
      setPagination(prev => ({ ...prev, total: p.total || 0 }));
    } catch { /* 拦截器已处理 */ }
    finally { setLoading(false); }
  }, [filters, pagination.current, pagination.pageSize]);

  useEffect(() => { fetchList(); }, [fetchList]);

  // ── 创建作品 ─────────────────────────────────────────────────
  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields();
      setCreateLoading(true);

      const formData = new FormData();
      formData.append('title', values.title);
      formData.append('category', values.category);
      formData.append('description', values.description || '');

      // 如果有图片文件
      if (values.images?.fileList) {
        values.images.fileList.forEach((f: any) => {
          formData.append('images', f.originFileObj);
        });
      }

      await createWorkApi(formData);
      message.success('作品创建成功');
      setCreateOpen(false);
      createForm.resetFields();
      fetchList();
    } catch { /* 拦截器处理 */ }
    finally { setCreateLoading(false); }
  };

  // ── 删除作品 ─────────────────────────────────────────────────
  const handleDelete = async (work_id: string) => {
    try {
      await deleteWorkApi(work_id);
      message.success('作品已删除');
      fetchList();
    } catch { /* */ }
  };

  // ── 提取DNA ──────────────────────────────────────────────────
  const handleExtractDna = async (work_id: string) => {
    setActionLoading(work_id);
    try {
      await extractDnaApi(work_id);
      message.success('DNA提取任务已触发，请稍后刷新查看结果');
      setTimeout(() => fetchList(), 2000);
    } catch { /* */ }
    finally { setActionLoading(null); }
  };

  // ── 上链存证 ─────────────────────────────────────────────────
  const handleCertify = async (work_id: string) => {
    setActionLoading(work_id);
    try {
      await createCertificateApi(work_id);
      message.success('上链存证成功');
      fetchList();
    } catch { /* */ }
    finally { setActionLoading(null); }
  };

  // ── 发布到网络 ────────────────────────────────────────────────
  const handlePublish = async (work_id: string) => {
    setActionLoading(work_id);
    try {
      const res = await publishWorkApi(work_id) as any;
      message.success(res?.publish_type === 'ipfs'
        ? `已发布到 IPFS 网络`
        : '已生成本地离线存证');
    } catch { /* */ }
    finally { setActionLoading(null); }
  };

  // ── 上传显微图像 ─────────────────────────────────────────────
  const handleMicroUpload = async () => {
    if (microFiles.length === 0) {
      message.warning('请选择要上传的显微图像');
      return;
    }
    setMicroUploading(true);
    try {
      const formData = new FormData();
      microFiles.forEach(f => {
        formData.append('microscope_images', f.originFileObj as File);
      });
      await uploadMicroscopeApi(microWorkId, formData);
      message.success('显微图像上传成功');
      setMicroOpen(false);
      setMicroFiles([]);
      fetchList();
    } catch { /* */ }
    finally { setMicroUploading(false); }
  };

  // ── 表格列定义 ───────────────────────────────────────────────
  const columns: ColumnsType<WorkItem> = [
    {
      title: '作品编号',
      dataIndex: 'work_id',
      key: 'work_id',
      width: 120,
      ellipsis: true,
      render: (id: string) => <Text copyable style={{ fontSize: 12 }}>{id.slice(0, 8)}...</Text>,
    },
    { title: '作品名称', dataIndex: 'title', key: 'title', width: 160 },
    { title: '类别', dataIndex: 'category', key: 'category', width: 80 },
    {
      title: 'DNA状态',
      dataIndex: 'dna_status',
      key: 'dna_status',
      width: 100,
      render: (s: string) => {
        const m = dnaStatusMap[s] || { color: 'default', label: s };
        return <Tag color={m.color}>{m.label}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (t: string) => t || '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 460,
      render: (_, record) => (
        <Space size="small" wrap>
          <Button
            size="small"
            icon={<ScanOutlined />}
            loading={actionLoading === record.work_id}
            disabled={record.dna_status === 'processing'}
            onClick={() => handleExtractDna(record.work_id)}
          >
            提取DNA
          </Button>
          <Button
            size="small"
            icon={<UploadOutlined />}
            onClick={() => {
              setMicroWorkId(record.work_id);
              setMicroFiles([]);
              setMicroOpen(true);
            }}
          >
            显微图像
          </Button>
          <Button
            size="small"
            type="primary"
            icon={<SafetyCertificateOutlined />}
            loading={actionLoading === record.work_id}
            disabled={record.dna_status !== 'completed'}
            onClick={() => handleCertify(record.work_id)}
          >
            上链存证
          </Button>
          <Button
            size="small"
            icon={<CloudServerOutlined />}
            loading={actionLoading === record.work_id}
            disabled={record.dna_status !== 'completed'}
            onClick={() => handlePublish(record.work_id)}
          >
            发布网络
          </Button>
          <Popconfirm
            title="确认删除此作品？"
            onConfirm={() => handleDelete(record.work_id)}
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];


  // ── 渲染 ─────────────────────────────────────────────────────
  return (
    <>
      <PageHeader title="作品管理" subtitle="作品入库、DNA 提取、上链存证与联网发布" />

      <Card
        className="soft-card"
        title="作品列表"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => fetchList()}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
              新增作品
            </Button>
          </Space>
        }
      >
        <Table
          rowKey="work_id"
          columns={columns}
          dataSource={data}
          loading={loading}
          size="middle"
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: t => `共 ${t} 件作品`,
            onChange: (page, pageSize) => {
              setPagination(prev => ({ ...prev, current: page, pageSize }));
            },
          }}
          scroll={{ x: 900 }}
        />
      </Card>

      {/* 新增作品 Modal */}
      <Modal
        title="新增作品"
        open={createOpen}
        onOk={handleCreate}
        onCancel={() => { setCreateOpen(false); createForm.resetFields(); }}
        confirmLoading={createLoading}
        destroyOnClose
      >
        <Form form={createForm} layout="vertical" preserve={false}>
          <Form.Item name="title" label="作品名称" rules={[{ required: true }]}>
            <Input placeholder="请输入作品名称" />
          </Form.Item>
          <Form.Item name="category" label="作品类别" rules={[{ required: true }]}>
            <Select options={CATEGORIES.map(c => ({ label: c, value: c }))} placeholder="请选择类别" />
          </Form.Item>
          <Form.Item name="description" label="作品描述">
            <Input.TextArea rows={3} placeholder="请输入作品描述" />
          </Form.Item>
          <Form.Item name="images" label="作品图片" valuePropName="fileList" getValueFromEvent={e => e?.fileList}>
            <Upload listType="picture-card" maxCount={5} beforeUpload={() => false}>
              <div><PlusOutlined /><div style={{ marginTop: 8 }}>上传</div></div>
            </Upload>
          </Form.Item>
        </Form>
      </Modal>

      {/* 上传显微图像 Modal */}
      <Modal
        title="上传显微图像"
        open={microOpen}
        onOk={handleMicroUpload}
        onCancel={() => { setMicroOpen(false); setMicroFiles([]); }}
        confirmLoading={microUploading}
      >
        <Dragger
          multiple
          maxCount={5}
          fileList={microFiles}
          beforeUpload={() => false}
          onChange={({ fileList }) => setMicroFiles(fileList)}
          accept="image/*"
        >
          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
          <p>点击或拖拽显微图像到此区域上传</p>
          <p style={{ color: '#8c8c8c' }}>支持 JPG/PNG/WebP，最多5张</p>
        </Dragger>
      </Modal>
    </>
  );
}