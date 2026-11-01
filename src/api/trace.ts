/**
 * 文化DNA —— 溯源与鉴定 API 模块
 */
import request from './request';

export interface TimelineEvent {
  event_type: string;
  event_name: string;
  timestamp: string;
  detail: Record<string, any>;
}

export interface TraceResult {
  work_id: string;
  title: string;
  timeline: TimelineEvent[];
  total_events: number;
}

export interface VerifyResult {
  work_id: string;
  title: string;
  verification_type: string;
  ai_match_score: number;
  dna_verified: boolean;
  final_result: string;
  response_time_ms: number;
  result_label: string;
}

/** 获取作品溯源时间线 */
export function getTraceTimelineApi(work_id: string) {
  return request.get<any, TraceResult>(`/trace/${work_id}/timeline`);
}

/** AI+链上双重验证 */
export function verifyArtworkApi(data: { work_id: string }) {
  return request.post<any, VerifyResult>('/trace/verify', data);
}

/** 鉴定记录列表 */
export function listVerificationLogsApi(params: {
  page?: number;
  page_size?: number;
  work_id?: string;
  final_result?: string;
}) {
  return request.get('/trace/verification-logs', { params });
}

/** 所有权转让 */
export function transferOwnershipApi(work_id: string, to_owner_id: number) {
  return request.post(`/trace/${work_id}/transfer`, { to_owner_id });
}

/** 转让记录 */
export function listTransfersApi(work_id: string) {
  return request.get(`/trace/${work_id}/transfers`);
}