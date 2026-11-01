/**
 * 文化DNA —— 网络发布/同步台账 API 模块
 */
import request from './request';

export interface PublishRecord {
  id: number;
  work_id: string;
  work_title: string;
  publish_type: string;
  cid: string;
  resource_url: string;
  status: string;
  message: string;
  created_at: string;
}

export interface PublishResult {
  work_id: string;
  work_title: string;
  publish_type: string;
  cid: string;
  resource_url: string;
  status: string;
  message: string;
  created_at: string;
}

/** 将已提取DNA的作品发布到网络（IPFS + 离线降级） */
export function publishWorkApi(work_id: string) {
  return request.post<any, PublishResult>(`/publish/${work_id}`);
}

/** 分页查询发布台账 */
export function listPublishApi(params: {
  page?: number;
  page_size?: number;
  keyword?: string;
}) {
  return request.get('/publish/', { params });
}