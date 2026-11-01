/**
 * 文化DNA —— 品牌标识（印章 + 名称 + 副标题）
 * 统一在侧边栏 / 顶栏 / 登录页使用，保证品牌一致性。
 */
import React from 'react';
import { FONT_SERIF } from '../theme';
import SealLogo from './SealLogo';

interface BrandLogoProps {
  /** 侧边栏折叠时只显示印章 */
  collapsed?: boolean;
  showSubtitle?: boolean;
  size?: number;
}

export default function BrandLogo({ collapsed = false, showSubtitle = true, size = 34 }: BrandLogoProps) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, overflow: 'hidden' }}>
      <SealLogo size={size} char="文" />
      {!collapsed && (
        <div style={{ lineHeight: 1.25, whiteSpace: 'nowrap' }}>
          <div
            style={{
              fontFamily: FONT_SERIF,
              fontWeight: 700,
              fontSize: 17,
              letterSpacing: 1,
              color: '#2C251E',
            }}
          >
            文化DNA
          </div>
          {showSubtitle && (
            <div style={{ fontSize: 11, color: '#A79C8C', marginTop: 2 }}>
              非遗作品确权溯源
            </div>
          )}
        </div>
      )}
    </div>
  );
}