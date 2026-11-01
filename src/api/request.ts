/**
 * 文化DNA —— Axios 请求封装
 * 统一拦截器：Token注入、401处理、错误提示
 */
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { message } from 'antd';
import { getToken, logout } from '../utils/auth';

// 桌面版：使用 Electron 预加载暴露的后端地址，或 Vite 代理的 /api
const BACKEND_BASE_URL = (window as any).electronAPI?.getBackendUrl?.() || '';

const request = axios.create({
  baseURL: BACKEND_BASE_URL ? `${BACKEND_BASE_URL}/api` : '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// ── 请求拦截器：注入 Bearer Token ──────────────────────────────
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error),
);

// ── 响应拦截器：统一错误处理 ────────────────────────────────────
request.interceptors.response.use(
  (response) => {
    const { code, message: msg } = response.data;
    if (code !== 0 && code !== undefined) {
      message.error(msg || '请求失败');
      return Promise.reject(new Error(msg));
    }
    return response.data.data;
  },
  (error: AxiosError<{ message?: string }>) => {
    if (error.response?.status === 401) {
      const url = error.config?.url || '';
      const isAuthRequest = url.includes('/auth/login') || url.includes('/auth/register');
      if (isAuthRequest) {
        // 登录/注册失败（密码错误等）是业务错误，不触发登出
        message.error(error.response?.data?.message || '用户名或密码错误');
      } else {
        message.error('登录已过期，请重新登录');
        logout();
      }
    } else if (error.response?.status === 500) {
      message.error('服务器内部错误');
    } else if (error.response) {
      // 业务错误（400/403/404/409 等）：展示后端返回的具体原因，
      // 避免调用方用空 catch 导致操作失败时无任何反馈
      message.error(error.response?.data?.message || '操作失败');
    } else if (error.message === 'Network Error') {
      // 桌面版：提示后端正在启动，而不是"网络错误"
      const isDesktop = !!(window as any).electronAPI;
      if (isDesktop) {
        message.error('后端服务正在启动中，请稍候再试');
      } else {
        message.error('网络连接失败，请检查后端服务');
      }
    }
    return Promise.reject(error);
  },
);

export default request;