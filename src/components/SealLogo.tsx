/**
 * 文化DNA —— 印章 Logo
 * 朱砂底 + 内框 + 白色宋体字样，纯 CSS 实现，不生成任何图片。
 */
import React from 'react';
import { FONT_SERIF } from '../theme';

interface SealLogoProps {
  size?: number;
  char?: string;
  /** 圆形印章（经典姓名章也常用方形，默认方形更稳重大气） */
  round?: boolean;
}

export default function SealLogo({ size = 36, char = '文', round = false }: SealLogoProps) {
  const inner = Math.max(2, Math.round(size * 0.09));
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: round ? '50%' : Math.round(size * 0.2),
        background: 'linear-gradient(135deg, #A8432F 0%, #8A3526 100%)',
        border: '1px solid #7E2F20',
        position: 'relative',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        boxShadow: '0 2px 6px rgba(126, 47, 32, 0.28)',
      }}
    >
      {/* 印章内框 */}
      <div
        style={{
          position: 'absolute',
          inset: inner,
          border: '1px solid rgba(255, 255, 255, 0.55)',
          borderRadius: round ? '50%' : Math.round(size * 0.12),
        }}
      />
      <span
        style={{
          color: '#fff',
          fontFamily: FONT_SERIF,
          fontSize: size * 0.52,
          fontWeight: 700,
          lineHeight: 1,
          transform: 'translateY(-1px)',
        }}
      >
        {char}
      </span>
    </div>
  );
}