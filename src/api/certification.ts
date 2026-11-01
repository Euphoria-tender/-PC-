/**
 * 文化DNA —— 身份认证申请 API 模块
 */
import request from './request';
import type { PaginatedResult } from './admin';

export interface RoleApplication {
  id: number;
  target_role: string;
  real_name: string;
  phone: string;
  materials: string;
  status: string;
  review_comment: string;
  reviewer_name: string;
  applicant_username: string;
  created_at: string;
  reviewed_at: string;
}

/** 提交身份认证申请 */
export function applyRoleApi(data: {
  target_role: string;
  real_name: string;
  phone?: string;
  materials: string;
}) {
  return request.post('/certification', data);
}

/** 我的申请记录 */
export function listMyApplicationsApi() {
  return request.get<any, { items: RoleApplication[] }>('/certification/mine');
}

/** 管理员：分页查询认证申请 */
export function listApplicationsApi(params: {
  page?: number;
  page_size?: number;
  status?: string;
  keyword?: string;
}) {
  return request.get<any, PaginatedResult<RoleApplication>>('/certification', { params });
}

/** 管理员：审核申请 */
export function reviewApplicationApi(id: number, data: {
  status: string;
  review_comment?: string;
}) {
  return request.put(`/certification/${id}`, data);
}