/**
 * 文化DNA —— 后端地址 / 静态资源地址辅助
 * 桌面版由 preload 暴露 getBackendUrl；开发态经 Vite 代理。
 */

/** 后端服务基地址（形如 http://127.0.0.1:5500，或空字符串表示走同源代理） */
export function getBackendBase(): string {
  return (window as any).electronAPI?.getBackendUrl?.() || '';
}

/** 将后台上传的图片相对路径拼成完整可访问 URL（统一处理 /uploads 前缀） */
export function imgUrl(path?: string | null): string {
  if (!path) return '';
  if (/^https?:\/\//i.test(path)) return path; // 已是完整 URL
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${getBackendBase()}/uploads${normalized}`;
}