/**
 * 文化DNA —— 用户平台布局（普通用户使用 · 国风）
 * 顶部标题栏 + 底部标签导航
 */
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Avatar, Dropdown, Typography, theme } from 'antd';
import {
  ExperimentOutlined,
  VerifiedOutlined,
  CloudUploadOutlined,
  UserOutlined,
  LogoutOutlined,
  FileSearchOutlined,
  AuditOutlined,
  IdcardOutlined,
} from '@ant-design/icons';
import { getUser, logout } from '../utils/auth';
import { ROLE_ACCESS } from '../constants';
import BrandLogo from './BrandLogo';

const { Header, Content, Footer } = Layout;
const { Text } = Typography;
const { useToken } = theme;

// 普通用户可见的菜单（底部标签栏）
const userTabItems = [
  { key: '/identify', icon: <ExperimentOutlined />, label: 'AI 鉴定' },
  { key: '/upload', icon: <CloudUploadOutlined />, label: '作品上传' },
  { key: '/verify', icon: <VerifiedOutlined />, label: '证书验证' },
  { key: '/trace', icon: <FileSearchOutlined />, label: '溯源查询' },
  { key: '/review', icon: <AuditOutlined />, label: '专家审核' },
  { key: '/certify', icon: <IdcardOutlined />, label: '身份认证' },
];

export default function UserLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = getUser();
  const { token } = useToken();

  // 按角色过滤底部标签：传承人可见「作品上传」，普通用户/鉴定师仅查询
  const role = user?.role || 'user';
  const allowed = ROLE_ACCESS[role] || ROLE_ACCESS.user;
  const tabItems = userTabItems.filter((t) => allowed.includes(t.key));

  const selectedKey = '/' + location.pathname.split('/')[1];

  const handleTabClick = (info: { key: string }) => {
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

  return (
    <Layout className="paper-bg" style={{ minHeight: '100vh' }}>
      {/* 顶部栏 */}
      <Header
        style={{
          background: token.colorBgContainer,
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
          boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
        }}
      >
        <BrandLogo size={32} />

        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
          <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10 }}>
            <Avatar size="small" icon={<UserOutlined />} style={{ background: token.colorPrimary }} />
            <Text style={{ fontSize: 14 }}>{user?.real_name || user?.username}</Text>
          </div>
        </Dropdown>
      </Header>

      {/* 内容区 */}
      <Content
        style={{
          padding: '24px',
          maxWidth: 1400,
          width: '100%',
          margin: '0 auto',
          flex: 1,
        }}
      >
        <Outlet />
      </Content>

      {/* 底部标签栏 */}
      <Footer
        style={{
          background: token.colorBgContainer,
          padding: 0,
          borderTop: `1px solid ${token.colorBorderSecondary}`,
          position: 'sticky',
          bottom: 0,
          zIndex: 100,
        }}
      >
        <Menu
          mode="horizontal"
          selectedKeys={[selectedKey]}
          items={tabItems}
          onClick={handleTabClick}
          style={{
            justifyContent: 'center',
            borderBottom: 'none',
            minHeight: 56,
            lineHeight: '56px',
          }}
        />
      </Footer>
    </Layout>
  );
}