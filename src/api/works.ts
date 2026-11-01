/**
 * 文化DNA —— 作品管理 API 模块
 */
import request from './request';

export interface WorkItem {
  id: number;
  work_id: string;
  title: string;
  category: string;
  description: string;
  images: string[];
  dna_status: string;
  created_at: string;
  updated_at: string;
  owner_name: string;
}

export interface WorkListParams {
  page?: number;
  page_size?: number;
  category?: string;
  dna_status?: string;
  keyword?: string;
}

export function listWorksApi(params: WorkListParams) {
  return request.get('/works/', { params });
}

export function getWorkApi(work_id: string) {
  return request.get(`/works/${work_id}`);
}

export function createWorkApi(formData: FormData) {
  return request.post('/works/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

export function updateWorkApi(work_id: string, data: Record<string, any>) {
  return request.put(`/works/${work_id}`, data);
}

export function deleteWorkApi(work_id: string) {
  return request.delete(`/works/${work_id}`);
}

export function extractDnaApi(work_id: string) {
  return request.post(`/works/${work_id}/extract-dna`);
}

export function uploadMicroscopeApi(work_id: string, formData: FormData) {
  return request.post(`/works/${work_id}/upload-micro`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}