/**
 * 文化DNA —— 页面标题栏
 * 朱砂竖条 + 宋体标题 + 副标题，右侧可挂操作（extra）。
 */
import React from 'react';
import { Typography, Space } from 'antd';
import { FONT_SERIF } from '../theme';

const { Title, Text } = Typography;

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  extra?: React.ReactNode;
}

export default function PageHeader({ title, subtitle, extra }: PageHeaderProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: 16,
        flexWrap: 'wrap',
        marginBottom: 20,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <span
          style={{
            width: 4,
            height: 28,
            borderRadius: 2,
            background: '#A8432F',
            marginTop: 4,
            flexShrink: 0,
          }}
        />
        <div>
          <Title
            level={4}
            style={{ margin: 0, fontFamily: FONT_SERIF, fontWeight: 700, letterSpacing: 1 }}
          >
            {title}
          </Title>
          {subtitle && (
            <Text type="secondary" style={{ display: 'block', marginTop: 4, fontSize: 13 }}>
              {subtitle}
            </Text>
          )}
        </div>
      </div>
      {extra && <Space wrap>{extra}</Space>}
    </div>
  );
}