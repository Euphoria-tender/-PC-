/**
 * 文化DNA —— 本地参考图库 API 模块
 */
import request from './request';

export interface ReferenceItem {
  id: number;
  source: string;
  query: string;
  title: string;
  image_url: string;
  source_url: string;
  created_at: string;
}

export interface ReferenceList {
  items: ReferenceItem[];
  pagination: { total: number; page: number; page_size: number; total_pages: number };
  total_references?: number;
}

/** 分页查询本地参考图库（联网搜索入库的参考图片） */
export function listReferencesApi(params: {
  page?: number;
  page_size?: number;
  keyword?: string;
}) {
  return request.get<any, ReferenceList>('/references/', { params });
}