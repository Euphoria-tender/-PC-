/**
 * 文化DNA —— 路由配置
 * 两套布局：
 *  - 管理员(admin)：后台管理风格 MainLayout
 *  - 普通用户(user/inheritor/appraiser)：用户平台风格 UserLayout
 */
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import MainLayout from './components/MainLayout';
import UserLayout from './components/UserLayout';
import Login from './pages/Login';
import Works from './pages/Works';
import Review from './pages/Review';
import Certify from './pages/Certify';
import CertificationAdmin from './pages/CertificationAdmin';
import Certificates from './pages/Certificates';
import Trace from './pages/Trace';
import Statistics from './pages/Statistics';
import UserManagement from './pages/UserManagement';
import Dashboard from './pages/Dashboard';
import Identify from './pages/Identify';
import ArtworkUpload from './pages/ArtworkUpload';
import Verify from './pages/Verify';
import Publish from './pages/Publish';
import References from './pages/References';
import { isLoggedIn, getUser } from './utils/auth';
import { ROLE_ACCESS } from './constants';

/** 路由守卫：未登录跳转登录页 */
function PrivateRoute({ children }: { children: React.ReactNode }) {
  if (!isLoggedIn()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

/**
 * 角色路由守卫：
 * - admin 角色 → 管理后台布局
 * - 其他角色 → 用户平台布局
 * 同时防止普通用户访问管理员页面
 */
function RoleRouter() {
  const location = useLocation();
  const user = getUser();
  const role = user?.role || 'user';
  const isAdmin = role === 'admin';

  // 当前角色可访问的顶级路径；越权访问统一跳回 AI 鉴定
  const allowed = ROLE_ACCESS[role] || ROLE_ACCESS.user;
  const currentPath = '/' + location.pathname.split('/')[1];
  if (allowed && !allowed.includes(currentPath)) {
    return <Navigate to="/identify" replace />;
  }

  // 根据角色返回不同布局
  if (isAdmin) {
    return (
      <PrivateRoute>
        <MainLayout />
      </PrivateRoute>
    );
  }

  return (
    <PrivateRoute>
      <UserLayout />
    </PrivateRoute>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/*" element={<RoleRouter />}>
        {/* 通用页面（所有角色可见） */}
        <Route index element={<Navigate to="/identify" replace />} />
        <Route path="identify" element={<Identify />} />
        <Route path="verify" element={<Verify />} />
        <Route path="trace" element={<Trace />} />
        <Route path="certify" element={<Certify />} />

        {/* 创作/管理类页面（admin/inheritor/appraiser 可见）
            普通用户访问会被 MainLayout 菜单过滤，但路由仍可达
            由 RoleRouter 中的路径检查处理重定向 */}
        <Route path="upload" element={<ArtworkUpload />} />
        <Route path="works" element={<Works />} />
        <Route path="review" element={<Review />} />
        <Route path="certificates" element={<Certificates />} />
        <Route path="publish" element={<Publish />} />
        <Route path="references" element={<References />} />

        {/* 管理员专属页面 */}
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="statistics" element={<Statistics />} />
        <Route path="users" element={<UserManagement />} />
        <Route path="certifications" element={<CertificationAdmin />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
