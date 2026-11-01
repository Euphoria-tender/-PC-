/**
 * 文化DNA —— 识别相关 API 调用
 */
import request from './request';

/** 识别结果匹配项 */
export interface IdentifyMatch {
  work_id: string;
  title: string;
  category: string;
  description: string;
  similarity: number;
  is_match: boolean;
  dna_hash: string;
  owner_name: string;
  images: string[];
  source_url: string;
}

/** 识别响应 */
export interface IdentifyResponse {
  matches: IdentifyMatch[];
  total_in_database: number;
  response_time_ms: number;
}

/** 联网比对参考项 */
export interface IdentifyOnlineMatch {
  title: string;
  source_url: string;
  image_url: string;
  similarity: number;
  cnn_similarity: number;
  dhash_similarity: number;
}

/** 双向识别 · 联网鉴定响应 */
export interface IdentifyOnlineResponse {
  local: IdentifyResponse;
  online: {
    query: string;
    available: boolean;
    results: IdentifyOnlineMatch[];
  };
  response_time_ms: number;
}

/**
 * AI 特征点识别
 * 上传图片，在数据库中搜索匹配的作品
 */
export async function identifyApi(
  imageFile: File,
  topK: number = 5,
): Promise<IdentifyResponse> {
  const formData = new FormData();
  formData.append('identify_image', imageFile);
  formData.append('top_k', String(topK));

  return request.post('/identify', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }) as Promise<IdentifyResponse>;
}

/**
 * 双向识别 · 联网鉴定
 * 上传图片，本地识别 + 联网搜索参考作品并交叉比对
 */
export async function identifyOnlineApi(
  imageFile: File,
  topK: number = 5,
  query?: string,
): Promise<IdentifyOnlineResponse> {
  const formData = new FormData();
  formData.append('identify_image', imageFile);
  formData.append('top_k', String(topK));
  if (query) formData.append('query', query);

  return request.post('/identify/online', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }) as Promise<IdentifyOnlineResponse>;
}

// NOTE: extractDnaApi / uploadMicroImagesApi 已统一由 src/api/works.ts 提供，
// 此处不再重复定义，避免同一端点维护多份契约。