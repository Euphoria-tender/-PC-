/**
 * 文化DNA —— 数据统计 API 模块
 */
import request from './request';

export interface OverviewData {
  total_works: number;
  total_certificates: number;
  total_verifications: number;
  total_users: number;
  total_fingerprints: number;
  total_references: number;
  total_published: number;
  today_works: number;
  today_certificates: number;
  today_verifications: number;
  verification_pass_rate: number;
  dna_completion_rate: number;
}

export interface TrendItem {
  date: string;
  certificates: number;
  verifications: number;
}

export interface CategoryItem {
  category: string;
  count: number;
  percentage: number;
}

export interface CreatorItem {
  user_id: number;
  real_name: string;
  username: string;
  work_count: number;
  cert_count: number;
  verification_pass_rate: number;
}

export function getOverviewApi() {
  return request.get<any, OverviewData>('/statistics/overview');
}

export function getTrendApi(days: number = 30) {
  return request.get<any, { days: number; trend: TrendItem[] }>('/statistics/trend', {
    params: { days },
  });
}

export function getCategoryApi() {
  return request.get<any, { total: number; categories: CategoryItem[] }>(
    '/statistics/category',
  );
}

export function getTopCreatorsApi() {
  return request.get<any, { top_creators: CreatorItem[] }>(
    '/statistics/top-creators',
  );
}