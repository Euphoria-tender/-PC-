/**
 * 文化DNA —— 前端认证工具模块
 * Token 存储与获取、用户信息管理
 */

const TOKEN_KEY = 'cultural_dna_token';
const USER_KEY = 'cultural_dna_user';

export interface UserInfo {
  id: number;
  username: string;
  role: string;
  real_name: string;
  phone: string;
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function setUser(user: UserInfo): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getUser(): UserInfo | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function removeUser(): void {
  localStorage.removeItem(USER_KEY);
}

export function isLoggedIn(): boolean {
  return !!getToken();
}

export function logout(): void {
  removeToken();
  removeUser();
  // HashRouter 下必须用 hash 跳转；location.href 在 Electron file:// 下会指向不存在的 file:///login
  window.location.hash = '#/login';
}