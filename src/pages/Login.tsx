/**
 * 文化DNA —— 登录页
 */
import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Form, Input, Button, Typography, message, Tabs, Modal,
  Alert, Spin
} from 'antd';
import {
  UserOutlined, LockOutlined, PhoneOutlined,
  CheckCircleOutlined, LoadingOutlined,
} from '@ant-design/icons';
import { loginApi, registerApi, changePasswordApi, LoginResult } from '../api/auth';
import { setToken, setUser, logout } from '../utils/auth';
import BrandLogo from '../components/BrandLogo';
import axios from 'axios';

const { Text } = Typography;

// 后端服务状态
type BackendStatus = 'checking' | 'loading' | 'ready' | 'error';

export default function Login() {
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('login');
  const [changePwdModalOpen, setChangePwdModalOpen] = useState(false);
  const [changePwdLoading, setChangePwdLoading] = useState(false);
  const [changePwdForm] = Form.useForm();
  const navigate = useNavigate();

  // 后端服务状态检测
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('checking');
  const [waitSeconds, setWaitSeconds] = useState(0);
  const checkRef = useRef<number | null>(null);

  const BACKEND_BASE_URL = (window as any).electronAPI?.getBackendUrl?.() || '';
  const isDesktop = !!BACKEND_BASE_URL;

  /** 检测后端是否就绪 */
  const checkBackend = async (): Promise<boolean> => {
    try {
      await axios.get(`${BACKEND_BASE_URL}/api/auth/profile`, { timeout: 3000 });
      return true;
    } catch (err: any) {
      // 401 说明后端已启动（只是需要登录）
      if (err.response?.status === 401) return true;
      return false;
    }
  };

  /** 轮询检测后端状态 */
  useEffect(() => {
    if (!isDesktop) {
      setBackendStatus('ready');
      return;
    }

    let retries = 0;
    const maxRetries = 60; // 最多等 60 次 × 1秒 = 60秒

    const poll = async () => {
      retries++;
      setWaitSeconds(retries);
      const ok = await checkBackend();
      if (ok) {
        setBackendStatus('ready');
        return;
      }
      if (retries < 2) {
        setBackendStatus('loading');
      }
      if (retries >= maxRetries) {
        setBackendStatus('error');
        return;
      }
      checkRef.current = window.setTimeout(poll, 1000);
    };

    poll();

    return () => {
      if (checkRef.current) clearTimeout(checkRef.current);
    };
  }, [isDesktop]);

  /** 登录 */
  const handleLogin = async (values: { username: string; password: string }) => {
    if (isDesktop && backendStatus !== 'ready') {
      message.warning('后端服务正在启动中，请稍候...');
      return;
    }
    setLoading(true);
    try {
      const res: LoginResult = await loginApi(values);
      setToken(res.access_token);
      setUser(res.user);

      if (res.must_change_password) {
        // 首次登录，弹出修改密码弹窗
        setChangePwdModalOpen(true);
      } else {
        message.success('登录成功');
        // 根据角色跳转：管理员进后台，普通用户进用户平台首页
        if (res.user?.role === 'admin') {
          navigate('/dashboard', { replace: true });
        } else {
          navigate('/identify', { replace: true });
        }
      }
    } catch {
      // 错误已在拦截器中提示
    } finally {
      setLoading(false);
    }
  };

  /** 首次登录修改密码 */
  const handleChangePassword = async (values: { old_password: string; new_password: string }) => {
    setChangePwdLoading(true);
    try {
      await changePasswordApi(values);
      message.success('密码修改成功，请重新登录');
      setChangePwdModalOpen(false);
      changePwdForm.resetFields();
      // 清除登录态，让用户用新密码重新登录
      logout();
    } catch {
      // 错误已在拦截器中提示
    } finally {
      setChangePwdLoading(false);
    }
  };

  /** 注册 */
  const handleRegister = async (values: {
    username: string;
    password: string;
    real_name: string;
    phone: string;
  }) => {
    if (isDesktop && backendStatus !== 'ready') {
      message.warning('后端服务正在启动中，请稍候...');
      return;
    }
    setLoading(true);
    try {
      await registerApi({ ...values, role: 'user' });
      message.success('注册成功，请登录');
      setActiveTab('login');
    } catch {
      // 错误已在拦截器中提示
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: 20 }}>
          <BrandLogo size={42} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 16, width: '86%' }}>
            <span style={{ height: 1, flex: 1, background: 'linear-gradient(90deg, transparent, #D9C39A)' }} />
            <span style={{ color: '#B98A4F', fontSize: 12, letterSpacing: 4, whiteSpace: 'nowrap' }}>
              确权 · 溯源 · 可信
            </span>
            <span style={{ height: 1, flex: 1, background: 'linear-gradient(90deg, #D9C39A, transparent)' }} />
          </div>
        </div>

        {/* 后端服务状态提示（桌面版显示） */}
        {isDesktop && backendStatus === 'loading' && (
          <Alert
            type="info"
            showIcon
            icon={<Spin indicator={<LoadingOutlined spin />} />}
            message={`后端服务正在启动，请稍候...（${waitSeconds}s）`}
            description="首次启动可能需要 20-30 秒"
            style={{ marginBottom: 16 }}
          />
        )}
        {isDesktop && backendStatus === 'ready' && (
          <Alert
            type="success"
            showIcon
            icon={<CheckCircleOutlined />}
            message="服务就绪"
            style={{ marginBottom: 16 }}
          />
        )}
        {isDesktop && backendStatus === 'error' && (
          <Alert
            type="error"
            showIcon
            message="后端服务启动失败"
            description="请尝试重启应用，如仍无法使用请联系技术支持。"
            style={{ marginBottom: 16 }}
          />
        )}

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          centered
          items={[
            {
              key: 'login',
              label: '登录',
              children: (
                <Form onFinish={handleLogin} size="large" autoComplete="off">
                  <Form.Item
                    name="username"
                    rules={[{ required: true, message: '请输入用户名' }]}
                  >
                    <Input prefix={<UserOutlined />} placeholder="用户名" />
                  </Form.Item>
                  <Form.Item
                    name="password"
                    rules={[{ required: true, message: '请输入密码' }]}
                  >
                    <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                  </Form.Item>
                  <Form.Item>
                    <Button
                      type="primary"
                      htmlType="submit"
                      loading={loading}
                      block
                      disabled={isDesktop && backendStatus !== 'ready'}
                    >
                      登 录
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: 'register',
              label: '注册',
              children: (
                <Form onFinish={handleRegister} size="large" autoComplete="off">
                  <Form.Item
                    name="username"
                    rules={[
                      { required: true, message: '请输入用户名' },
                      { min: 3, message: '用户名至少3个字符' },
                    ]}
                  >
                    <Input prefix={<UserOutlined />} placeholder="用户名" />
                  </Form.Item>
                  <Form.Item
                    name="real_name"
                    rules={[{ required: true, message: '请输入真实姓名' }]}
                  >
                    <Input prefix={<UserOutlined />} placeholder="真实姓名" />
                  </Form.Item>
                  <Form.Item
                    name="phone"
                    rules={[{ required: true, message: '请输入手机号' }]}
                  >
                    <Input prefix={<PhoneOutlined />} placeholder="手机号" />
                  </Form.Item>
                  <Form.Item
                    name="password"
                    rules={[
                      { required: true, message: '请输入密码' },
                      { min: 6, message: '密码至少6个字符' },
                    ]}
                  >
                    <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                  </Form.Item>
                  <Form.Item>
                    <Button
                      type="primary"
                      htmlType="submit"
                      loading={loading}
                      block
                      disabled={isDesktop && backendStatus !== 'ready'}
                    >
                      注 册
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
          ]}
        />
      </div>

      {/* 首次登录强制修改密码弹窗 */}
      <Modal
        title="首次登录 - 请修改密码"
        open={changePwdModalOpen}
        onCancel={() => {
          setChangePwdModalOpen(false);
          changePwdForm.resetFields();
        }}
        footer={null}
        maskClosable={false}
        closable={false}
      >
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          出于安全考虑，首次登录需要修改默认密码。
        </Text>
        <Form
          form={changePwdForm}
          onFinish={handleChangePassword}
          size="large"
          autoComplete="off"
        >
          <Form.Item
            name="old_password"
            rules={[{ required: true, message: '请输入当前密码' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="当前密码" />
          </Form.Item>
          <Form.Item
            name="new_password"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '密码至少6个字符' },
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="新密码" />
          </Form.Item>
          <Form.Item
            name="confirm_password"
            dependencies={['new_password']}
            rules={[
              { required: true, message: '请确认新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="确认新密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={changePwdLoading} block>
              确认修改
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
