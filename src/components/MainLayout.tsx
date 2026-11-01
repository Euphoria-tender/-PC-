/**
 * 文化DNA —— 主布局组件（侧边栏 + 内容区 · 国风）
 */
import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, theme, Dropdown, Avatar } from 'antd';
import {
  PictureOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
  BarChartOutlined,
  LogoutOutlined,
  UserOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  TeamOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  CloudUploadOutlined,
  VerifiedOutlined,
  CloudServerOutlined,
  DatabaseOutlined,
  AuditOutlined,
  SolutionOutlined,
} from '@ant-design/icons';
import { getUser, logout } from '../utils/auth';
import BrandLogo from './BrandLogo';

const { Header, Sider, Content } = Layout;

const allMenuItems: { key: string; icon: React.ReactNode; label: string; roles: string[] }[] = [
  { key: '/identify', icon: <ExperimentOutlined />, label: 'AI 鉴定', roles: ['admin', 'inheritor', 'appraiser', 'user'] },
  { key: '/upload', icon: <CloudUploadOutlined />, label: '作品上传', roles: ['admin', 'inheritor', 'appraiser'] },
  { key: '/verify', icon: <VerifiedOutlined />, label: '证书验证', roles: ['admin', 'inheritor', 'appraiser', 'user'] },
  { key: '/dashboard', icon: <DashboardOutlined />, label: '管理面板', roles: ['admin'] },
  { key: '/works', icon: <PictureOutlined />, label: '作品管理', roles: ['admin', 'inheritor', 'appraiser'] },
  { key: '/review', icon: <AuditOutlined />, label: '专家审核', roles: ['admin', 'appraiser'] },
  { key: '/certificates', icon: <SafetyCertificateOutlined />, label: '存证管理', roles: ['admin', 'inheritor', 'appraiser'] },
  { key: '/publish', icon: <CloudServerOutlined />, label: '网络发布', roles: ['admin', 'inheritor', 'appraiser'] },
  { key: '/references', icon: <DatabaseOutlined />, label: '本地图库', roles: ['admin', 'inheritor', 'appraiser'] },
  { key: '/trace', icon: <SearchOutlined />, label: '溯源查询', roles: ['admin', 'inheritor', 'appraiser', 'user'] },
  { key: '/statistics', icon: <BarChartOutlined />, label: '数据统计', roles: ['admin'] },
  { key: '/users', icon: <TeamOutlined />, label: '用户管理', roles: ['admin'] },
  { key: '/certifications', icon: <SolutionOutlined />, label: '认证管理', roles: ['admin'] },
];

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const user = getUser();
  const { token } = theme.useToken();

  // 根据角色过滤菜单
  const userRole = user?.role || 'user';
  const menuItems = allMenuItems.filter((item) => item.roles.includes(userRole));

  const handleMenuClick = (info: { key: string }) => {
    navigate(info.key);
  };

  const userMenuItems = [
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: () => logout(),
    },
  ];

  // 从路径中提取当前菜单选中项
  const selectedKey = '/' + location.pathname.split('/')[1];

  return (
    <Layout className="paper-bg" style={{ minHeight: '100vh' }}>
      {/* 侧边栏 */}
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        breakpoint="lg"
        width={220}
        style={{ background: token.colorBgContainer, borderRight: `1px solid ${token.colorBorderSecondary}` }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: collapsed ? 'center' : 'flex-start',
            justifyContent: 'center',
            paddingLeft: collapsed ? 0 : 24,
            flexDirection: 'column',
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <BrandLogo collapsed={collapsed} showSubtitle={!collapsed} />
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ borderRight: 0, padding: '8px 8px 24px' }}
        />
      </Sider>

      <Layout>
        {/* 顶部栏 */}
        <Header
          style={{
            padding: '0 24px',
            background: token.colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Avatar size="small" icon={<UserOutlined />} style={{ background: token.colorPrimary }} />
              <span style={{ fontSize: 14 }}>{user?.real_name || user?.username || '管理员'}</span>
            </div>
          </Dropdown>
        </Header>

        {/* 内容区 */}
        <Content
          style={{
            margin: 20,
            padding: 24,
            background: token.colorBgContainer,
            borderRadius: token.borderRadiusLG,
            minHeight: 280,
            overflow: 'auto',
            border: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <Outlet />
        </Content>

        <div
          style={{
            textAlign: 'center',
            padding: '4px 0 12px',
            fontSize: 12,
            color: token.colorTextTertiary,
          }}
        >
          文化DNA · 非遗作品确权溯源平台
        </div>
      </Layout>
    </Layout>
  );
}