/**
 * 文化DNA —— 统计卡片
 * 统一包装 antd Statistic，附带项目统一的柔白卡片风格。
 */
import React from 'react';
import { Card, Statistic } from 'antd';
import type { StatisticProps } from 'antd';

interface StatCardProps extends StatisticProps {
  /** 数值强调色（默认主色），可传朱红/青瓷等主题色 */
  accent?: string;
}

export default function StatCard({ accent, valueStyle, ...rest }: StatCardProps) {
  return (
    <Card
      style={{ height: '100%' }}
      styles={{ body: { padding: '18px 20px' } }}
      className="soft-card"
    >
      <Statistic
        {...rest}
        valueStyle={{ fontSize: 30, fontWeight: 600, ...(valueStyle as object), ...(accent ? { color: accent } : {}) }}
      />
    </Card>
  );
}