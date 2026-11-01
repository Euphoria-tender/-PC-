/**
 * 文化DNA —— 通用格式化 / 展示辅助
 */
import { palette } from '../theme';

/** 相似度(0-1) → 展示颜色 */
export function similarityColor(score: number): string {
  if (score >= 0.95) return palette.success;
  if (score >= 0.85) return palette.cinnabar;
  if (score >= 0.7) return palette.warning;
  return palette.error;
}

/** 相似度(0-1) → 百分比字符串 */
export function percent(score: number, digits = 1): string {
  return `${(score * 100).toFixed(digits)}%`;
}

/** 长文本截断（用于表格/列表展示唯一标识） */
export function truncate(text: string | undefined | null, len = 16): string {
  if (!text) return '';
  return text.length > len ? `${text.slice(0, len)}…` : text;
}