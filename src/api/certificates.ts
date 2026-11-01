/**
 * 文化DNA —— 证书与存证 API 模块
 */
import request from './request';

export interface CertificateItem {
  id: number;
  certificate_no: string;
  tx_id: string;
  block_height: number;
  chain_code: string;
  channel_name: string;
  status: string;
  created_at: string;
  work_title: string;
  work_id: string;
}

export function listCertificatesApi(params: {
  page?: number;
  page_size?: number;
  status?: string;
}) {
  return request.get('/certificates/', { params });
}

export function getCertificateApi(certificate_no: string) {
  return request.get(`/certificates/${certificate_no}`);
}

/** 触发DNA提取+上链存证 */
export function createCertificateApi(work_id: string) {
  return request.post(`/certificates/${work_id}`);
}

/** 查询存证状态 */
export function getCertStatusApi(work_id: string) {
  return request.get(`/certificates/${work_id}/status`);
}

/** 验证证书真伪 */
export function verifyCertificateApi(certificate_no: string) {
  return request.post(`/certificates/${certificate_no}/verify`);
}