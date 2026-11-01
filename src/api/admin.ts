/**
 * 文化DNA —— 管理员 API 模块
 */
import request from './request';

// ── 类型定义 ──────────────────────────────────────────────────

export interface UserItem {
  id: number;
  username: string;
  role: string;
  real_name: string;
  phone: string;
  openid: string;
  must_change_password: boolean;
  created_at: string;
}

export interface PaginatedResult<T> {
  items: T[];
  pagination: {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
  /** 用户列表专用：管理员总数（用于「至少保留一个管理员」保护） */
  total_admins?: number;
}

export interface DashboardData {
  total_users: number;
  total_works: number;
  total_certificates: number;
  total_verifications: number;
  pending_review_count: number;
  today_new_users: number;
  today_new_works: number;
}

export interface ArtworkReviewItem {
  id: number;
  work_id: string;
  title: string;
  category: string;
  description: string;
  images?: string[];
  dna_status: string;
  review_status: string;
  review_comment: string;
  review_grade?: string;
  owner_name: string;
  reviewer_name?: string;
  created_at: string;
}

// ── 用户管理 ──────────────────────────────────────────────────

export function listUsersApi(params: {
  page?: number;
  page_size?: number;
  keyword?: string;
  role?: string;
}) {
  return request.get<any, PaginatedResult<UserItem>>('/admin/users', { params });
}

export function createUserApi(data: {
  username: string;
  password: string;
  real_name: string;
  phone: string;
  role: string;
}) {
  return request.post('/admin/users', data);
}

export function updateUserApi(user_id: number, data: {
  real_name?: string;
  phone?: string;
  role?: string;
}) {
  return request.put(`/admin/users/${user_id}`, data);
}

export function deleteUserApi(user_id: number) {
  return request.delete(`/admin/users/${user_id}`);
}

export function resetUserPasswordApi(user_id: number, new_password: string) {
  return request.put(`/admin/users/${user_id}/reset-password`, { new_password });
}

// ── 仪表盘 ────────────────────────────────────────────────────

export function getDashboardApi() {
  return request.get<any, DashboardData>('/admin/dashboard');
}

// ── 作品审核 ──────────────────────────────────────────────────

export function listArtworksForReviewApi(params: {
  page?: number;
  page_size?: number;
  review_status?: string;
  keyword?: string;
}) {
  return request.get<any, PaginatedResult<ArtworkReviewItem>>('/admin/artworks', { params });
}

export function reviewArtworkApi(work_id: string, data: {
  review_status: string;
  review_comment?: string;
  review_grade?: string;
}) {
  return request.put(`/admin/artworks/${work_id}/review`, data);
}