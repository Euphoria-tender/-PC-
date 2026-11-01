/**
 * 文化DNA —— 管理面板（管理员）
 */
import { useState, useEffect } from 'react';
import { Card, Col, Row, Statistic } from 'antd';
import {
  UserOutlined, PictureOutlined, SafetyCertificateOutlined,
  SearchOutlined, ClockCircleOutlined, PlusCircleOutlined,
} from '@ant-design/icons';
import { getDashboardApi, DashboardData } from '../api/admin';
import PageHeader from '../components/PageHeader';
import { palette } from '../theme';

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardApi()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <PageHeader title="管理面板" subtitle="系统运行概览与关键指标一览" />

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={8}>
          <Card loading={loading} className="soft-card">
            <Statistic
              title="用户总数"
              value={data?.total_users || 0}
              prefix={<UserOutlined />}
              valueStyle={{ color: palette.cinnabar }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card loading={loading} className="soft-card">
            <Statistic
              title="作品总数"
              value={data?.total_works || 0}
              prefix={<PictureOutlined />}
              valueStyle={{ color: palette.gold }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card loading={loading} className="soft-card">
            <Statistic
              title="存证数量"
              value={data?.total_certificates || 0}
              prefix={<SafetyCertificateOutlined />}
              valueStyle={{ color: palette.success }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card loading={loading} className="soft-card">
            <Statistic
              title="验证次数"
              value={data?.total_verifications || 0}
              prefix={<SearchOutlined />}
              valueStyle={{ color: palette.celadon }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card
            loading={loading}
            className="soft-card"
            style={{ borderColor: data?.pending_review_count ? palette.warning : undefined }}
          >
            <Statistic
              title="待审核作品"
              value={data?.pending_review_count || 0}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: data?.pending_review_count ? palette.warning : undefined }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card loading={loading} className="soft-card">
            <Statistic
              title="今日新增作品"
              value={data?.today_new_works || 0}
              prefix={<PlusCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}