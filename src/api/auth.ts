/**
 * 文化DNA —— 认证 API 模块
 */
import request from './request';

export interface LoginParams {
  username: string;
  password: string;
}

export interface RegisterParams {
  username: string;
  password: string;
  real_name: string;
  phone: string;
  role?: string;
}

export interface LoginResult {
  access_token: string;
  refresh_token: string;
  user: {
    id: number;
    username: string;
    role: string;
    real_name: string;
    phone: string;
  };
  must_change_password?: boolean;
}

export function loginApi(params: LoginParams) {
  return request.post<any, LoginResult>('/auth/login', params);
}

export function registerApi(params: RegisterParams) {
  return request.post('/auth/register', params);
}

export function getProfileApi() {
  return request.get('/auth/profile');
}

export function changePasswordApi(params: { old_password: string; new_password: string }) {
  return request.put('/auth/change-password', params);
}

export function refreshTokenApi(refresh_token: string) {
  return request.post('/auth/refresh', { refresh_token });
}