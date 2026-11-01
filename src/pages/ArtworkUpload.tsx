/**
 * 文化DNA —— 作品上传 + DNA 提取页
 */
import { useState } from 'react';
import {
  Card, Form, Input, Select, Button, Upload, Steps,
  message, Typography, Result, Space, Descriptions, Tag, Spin,
} from 'antd';
import {
  UploadOutlined, ExperimentOutlined,
  CheckCircleOutlined, InboxOutlined,
} from '@ant-design/icons';
import PageHeader from '../components/PageHeader';
import { palette } from '../theme';
import { CATEGORIES } from '../constants';
import { createWorkApi, extractDnaApi, uploadMicroscopeApi } from '../api/works';

const { Text, Paragraph } = Typography;
const { Dragger } = Upload;
const { TextArea } = Input;

export default function ArtworkUpload() {
  const [form] = Form.useForm();
  const [currentStep, setCurrentStep] = useState(0);
  const [workImages, setWorkImages] = useState<File[]>([]);
  const [microImages, setMicroImages] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [createdWork, setCreatedWork] = useState<any>(null);
  const [dnaResult, setDnaResult] = useState<any>(null);

  /** 步骤1：创建作品 */
  const handleCreateWork = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      const formData = new FormData();
      formData.append('title', values.title);
      formData.append('category', values.category);
      formData.append('description', values.description || '');
      workImages.forEach((file) => {
        formData.append('images', file);
      });

      const work = await createWorkApi(formData as any);
      setCreatedWork(work);
      setCurrentStep(1);
      message.success('作品创建成功！');
    } catch (err: any) {
      if (err?.message) message.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  /** 步骤2：上传微观图像 */
  const handleUploadMicro = async () => {
    if (!createdWork) return;
    setLoading(true);

    try {
      if (microImages.length > 0) {
        const microFormData = new FormData();
        microImages.forEach((f) => microFormData.append('microscope_images', f));
        await uploadMicroscopeApi(createdWork.work_id, microFormData);
        message.success('微观图像上传成功！');
      }
      setCurrentStep(2);
    } catch (err: any) {
      if (err?.message) message.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  /** 步骤3：提取DNA */
  const handleExtractDna = async () => {
    if (!createdWork) return;
    setLoading(true);

    try {
      const result: any = await extractDnaApi(createdWork.work_id);
      setDnaResult(result);
      setCurrentStep(3);
      if (result.dna_status === 'completed') {
        message.success('DNA 特征提取成功！');
      }
    } catch (err: any) {
      if (err?.message) message.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const steps = [
    { title: '填写信息', description: '作品基本信息' },
    { title: '微观图像', description: '上传微观扫描图' },
    { title: '提取DNA', description: 'AI特征提取' },
    { title: '完成', description: '上链存证' },
  ];

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <PageHeader
        title="作品上传与 DNA 提取"
        subtitle="填写信息、上传微观图像、AI 提取视觉 DNA 指纹"
      />

      <Steps current={currentStep} items={steps} style={{ marginBottom: 32 }} />

      {/* 步骤 0：基本信息 */}
      {currentStep === 0 && (
        <Card title="作品基本信息" className="soft-card">
          <Form form={form} layout="vertical">
            <Form.Item
              name="title"
              label="作品名称"
              rules={[{ required: true, message: '请输入作品名称' }]}
            >
              <Input placeholder="如：清明上河图刺绣卷轴" />
            </Form.Item>

            <Form.Item
              name="category"
              label="作品分类"
              rules={[{ required: true, message: '请选择分类' }]}
            >
              <Select placeholder="选择分类">
                {CATEGORIES.map((cat) => (
                  <Select.Option key={cat} value={cat}>{cat}</Select.Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item name="description" label="作品描述">
              <TextArea rows={4} placeholder="描述作品的工艺特点、尺寸、材质等信息..." />
            </Form.Item>

            <Form.Item label="作品图片" required>
              <Dragger
                multiple
                beforeUpload={(file) => {
                  setWorkImages((prev) => [...prev, file]);
                  return false;
                }}
                accept="image/png,image/jpeg,image/jpg,image/webp"
                showUploadList
              >
                <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                <p className="ant-upload-text">点击或拖拽作品图片</p>
                <p className="ant-upload-hint">最多上传 5 张图片</p>
              </Dragger>
            </Form.Item>

            <Button
              type="primary"
              size="large"
              onClick={handleCreateWork}
              loading={loading}
              disabled={workImages.length === 0}
            >
              创建作品
            </Button>
          </Form>
        </Card>
      )}

      {/* 步骤 1：微观图像 */}
      {currentStep === 1 && (
        <Card title="微观扫描图像" className="soft-card">
          <Paragraph type="secondary">
            上传作品微观纹理扫描图像，用于提取更精细的 DNA 特征。此步骤可选，跳过则仅使用普通图片提取特征。
          </Paragraph>
          <Dragger
            multiple
            beforeUpload={(file) => {
              setMicroImages((prev) => [...prev, file]);
              return false;
            }}
            accept="image/png,image/jpeg,image/jpg,image/webp"
            showUploadList
          >
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p className="ant-upload-text">点击或拖拽微观扫描图像</p>
            <p className="ant-upload-hint">最多上传 5 张微观图像</p>
          </Dragger>
          <Space style={{ marginTop: 16 }}>
            <Button size="large" onClick={handleUploadMicro} loading={loading}>
              上传微观图像并继续
            </Button>
            <Button size="large" onClick={() => setCurrentStep(2)}>
              跳过此步骤
            </Button>
          </Space>
        </Card>
      )}

      {/* 步骤 2：提取DNA */}
      {currentStep === 2 && (
        <Card title="AI 特征提取" className="soft-card">
          <Paragraph type="secondary">
            系统将使用深度学习模型（ResNet50）提取作品视觉特征，生成128维 DNA 特征向量和 SHA-256 哈希值。
          </Paragraph>
          <div style={{ textAlign: 'center', padding: 24 }}>
            <ExperimentOutlined style={{ fontSize: 64, color: palette.cinnabar }} />
            <Paragraph style={{ marginTop: 16 }}>
              <Text>作品 "{createdWork?.title}" 已创建，准备提取 DNA 指纹</Text>
            </Paragraph>
            <Button
              type="primary"
              size="large"
              icon={<ExperimentOutlined />}
              onClick={handleExtractDna}
              loading={loading}
            >
              开始提取 DNA
            </Button>
          </div>
        </Card>
      )}

      {/* 步骤 3：完成 */}
      {currentStep === 3 && (
        <Card className="soft-card">
          <Result
            status="success"
            title="作品 DNA 提取完成！"
            subTitle={
              dnaResult?.dna_status === 'completed'
                ? 'AI 特征提取成功，数字指纹已生成。'
                : 'DNA 指纹提取中，请稍候...'
            }
          />
          {dnaResult && (
            <Descriptions bordered column={1} style={{ maxWidth: 500, margin: '0 auto' }}>
              <Descriptions.Item label="作品编号">
                <Text code>{createdWork?.work_id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="DNA 哈希">
                <Text code style={{ fontSize: 12 }}>{dnaResult.dna_hash}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={dnaResult.dna_status === 'completed' ? 'success' : 'processing'}>
                  {dnaResult.dna_status === 'completed' ? '已完成' : '处理中'}
                </Tag>
              </Descriptions.Item>
            </Descriptions>
          )}
          <div style={{ textAlign: 'center', marginTop: 24 }}>
            <Button type="primary" onClick={() => {
              setCurrentStep(0);
              setCreatedWork(null);
              setDnaResult(null);
              setWorkImages([]);
              setMicroImages([]);
              form.resetFields();
            }}>
              上传新作品
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}