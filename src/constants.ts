/**
 * 文化DNA —— 全局常量
 * 统一分散在各页面中的重复定义（品类 / 角色），避免口径不一致。
 */

/** 非遗作品类别（上传 / 作品管理 / 识别共用同一份） */
export const CATEGORIES = [
  '刺绣', '陶瓷', '木雕', '剪纸', '漆器',
  '紫砂', '景泰蓝', '竹编', '石雕', '青铜器', '其他',
];

/** 角色显示名 */
export const ROLE_LABELS: Record<string, string> = {
  admin: '管理员',
  inheritor: '传承人',
  appraiser: '鉴定师',
  user: '普通用户',
};

/** 角色 Tag 颜色 */
export const ROLE_COLORS: Record<string, string> = {
  admin: 'volcano',
  inheritor: 'geekblue',
  appraiser: 'gold',
  user: 'default',
};

/**
 * 各角色可访问的顶级路径（菜单过滤 + 路由守卫共用唯一口径）
 * - 传承人(inheritor)：可上传数据（作品上传） + 查询
 * - 普通用户(user) / 鉴定师(appraiser)：仅查询（AI 鉴定 / 证书验证 / 溯源查询）
 * 与后端 @inheritor_required（仅传承人/管理员可上传）保持一致。
 */
export const ROLE_ACCESS: Record<string, string[]> = {
  admin: ['/identify', '/upload', '/verify', '/trace', '/works', '/certificates', '/publish', '/references', '/review', '/certifications', '/dashboard', '/statistics', '/users'],
  inheritor: ['/identify', '/upload', '/verify', '/trace', '/certify'],
  appraiser: ['/identify', '/verify', '/trace', '/review', '/certify'],
  user: ['/identify', '/verify', '/trace', '/certify'],
};

/** DNA 提取状态映射（作品管理 / 上传共用） */
export const DNA_STATUS_MAP: Record<string, { color: string; label: string }> = {
  pending: { color: 'default', label: '待提取' },
  processing: { color: 'processing', label: '提取中' },
  completed: { color: 'success', label: '已提取' },
  failed: { color: 'error', label: '提取失败' },
};

/** 专家审核评级档位（与后端 admin.py _VALID_GRADES 保持一致） */
export const GRADE_OPTIONS = [
  { value: 'master', label: '大师级' },
  { value: 'premium', label: '精品级' },
  { value: 'excellent', label: '优良级' },
  { value: 'qualified', label: '合格级' },
];

/** 评级显示名 */
export const GRADE_LABELS: Record<string, string> = {
  master: '大师级',
  premium: '精品级',
  excellent: '优良级',
  qualified: '合格级',
};

/** 评级 Tag 颜色 */
export const GRADE_COLORS: Record<string, string> = {
  master: 'volcano',
  premium: 'gold',
  excellent: 'geekblue',
  qualified: 'default',
};