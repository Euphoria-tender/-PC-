/**
 * 文化DNA —— 数据统计页
 * 数字卡片 + 趋势折线图 + 品类饼图 + 活跃传承人排行榜
 */
import { useEffect, useState } from 'react';
import { Card, Col, Row, Statistic, Table, Typography, Spin, Empty, Progress, Space } from 'antd';
import {
  PictureOutlined, SafetyCertificateOutlined, SearchOutlined,
  CheckCircleOutlined, TrophyOutlined, DatabaseOutlined, CloudServerOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { ColumnsType } from 'antd/es/table';
import PageHeader from '../components/PageHeader';
import { palette } from '../theme';
import {
  getOverviewApi, getTrendApi, getCategoryApi, getTopCreatorsApi,
  OverviewData, TrendItem, CategoryItem, CreatorItem,
} from '../api/statistics';

const { Text } = Typography;

export default function Statistics() {
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [trend, setTrend] = useState<TrendItem[]>([]);
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const [creators, setCreators] = useState<CreatorItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      try {
        const [ov, tr, ca, tc] = await Promise.all([
          getOverviewApi(),
          getTrendApi(30),
          getCategoryApi(),
          getTopCreatorsApi(),
        ]);
        setOverview(ov);
        setTrend(tr.trend || []);
        setCategories(ca.categories || []);
        setCreators(tc.top_creators || []);
      } catch { /* */ }
      finally { setLoading(false); }
    };
    fetchAll();
  }, []);

  // ── 趋势折线图配置 ───────────────────────────────────────────
  const trendOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['存证数', '验证数'], top: 0 },
    grid: { left: 40, right: 20, top: 40, bottom: 30 },
    xAxis: {
      type: 'category',
      data: trend.map(t => t.date.slice(5)), // MM-DD
      axisLabel: { rotate: 45, fontSize: 10 },
    },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        name: '存证数',
        type: 'line',
        data: trend.map(t => t.certificates),
        smooth: true,
        itemStyle: { color: palette.cinnabar },
        areaStyle: { color: 'rgba(168,67,47,0.12)' },
      },
      {
        name: '验证数',
        type: 'line',
        data: trend.map(t => t.verifications),
        smooth: true,
        itemStyle: { color: palette.success },
        areaStyle: { color: 'rgba(78,138,95,0.12)' },
      },
    ],
  };

  // ── 品类饼图配置 ─────────────────────────────────────────────
  const pieOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', right: 0, top: 'center' },
    series: [
      {
        type: 'pie',
        radius: ['45%', '75%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: false,
        label: { show: false },
        emphasis: {
          label: { show: true, fontWeight: 'bold' },
        },
        data: categories.map(c => ({
          name: c.category,
          value: c.count,
        })),
      },
    ],
    color: [palette.cinnabar, palette.gold, palette.celadon, palette.success, palette.warning, palette.error],
  };

  // ── 排行榜列 ─────────────────────────────────────────────────
  const creatorColumns: ColumnsType<CreatorItem> = [
    {
      title: '排名',
      key: 'rank',
      width: 60,
      render: (_, __, i) => {
        const colors = [palette.error, palette.gold, palette.warning];
        return <Text strong style={{ color: i < 3 ? colors[i] : undefined }}>#{i + 1}</Text>;
      },
    },
    { title: '姓名', dataIndex: 'real_name', key: 'real_name' },
    {
      title: '作品数',
      dataIndex: 'work_count',
      key: 'work_count',
      align: 'center',
      sorter: (a, b) => a.work_count - b.work_count,
    },
    {
      title: '存证数',
      dataIndex: 'cert_count',
      key: 'cert_count',
      align: 'center',
      sorter: (a, b) => a.cert_count - b.cert_count,
    },
    {
      title: '验证通过率',
      dataIndex: 'verification_pass_rate',
      key: 'verification_pass_rate',
      align: 'center',
      width: 160,
      render: (rate: number) => (
        <Progress
          percent={rate}
          size="small"
          strokeColor={rate >= 80 ? palette.success : rate >= 60 ? palette.warning : palette.error}
          format={p => `${p?.toFixed(0)}%`}
        />
      ),
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" tip="加载统计数据中..." />
      </div>
    );
  }

  if (!overview) {
    return <Empty description="暂无统计数据" />;
  }

  return (
    <>
      <PageHeader title="数据统计" subtitle="存证、验证、作品与传承人的量化分析" />

      {/* 数字卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card className="soft-card">
            <Statistic
              title="存证总数"
              value={overview.total_certificates}
              prefix={<SafetyCertificateOutlined />}
              valueStyle={{ color: palette.cinnabar }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="soft-card">
            <Statistic
              title="验证总数"
              value={overview.total_verifications}
              prefix={<SearchOutlined />}
              valueStyle={{ color: palette.success }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="soft-card">
            <Statistic
              title="作品总数"
              value={overview.total_works}
              prefix={<PictureOutlined />}
              valueStyle={{ color: palette.gold }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="soft-card">
            <Statistic
              title="验证通过率"
              value={overview.verification_pass_rate}
              suffix="%"
              precision={1}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: palette.warning }}
            />
          </Card>
        </Col>
      </Row>

      {/* 本地数据库规模 */}
      <Card className="soft-card" title={<Space><DatabaseOutlined /> 本地数据库规模</Space>} style={{ marginBottom: 24 }}>
        <Row gutter={[16, 16]}>
          <Col xs={8}>
            <Statistic
              title="已提取指纹作品"
              value={overview.total_fingerprints}
              suffix="件"
              prefix={<SafetyCertificateOutlined />}
              valueStyle={{ color: palette.cinnabar }}
            />
          </Col>
          <Col xs={8}>
            <Statistic
              title="联网参考图库"
              value={overview.total_references}
              suffix="张"
              prefix={<PictureOutlined />}
              valueStyle={{ color: palette.celadon }}
            />
          </Col>
          <Col xs={8}>
            <Statistic
              title="网络发布存证"
              value={overview.total_published}
              suffix="条"
              prefix={<CloudServerOutlined />}
              valueStyle={{ color: palette.gold }}
            />
          </Col>
        </Row>
      </Card>

      {/* 今日概览 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={8}>
          <Card className="soft-card" size="small">
            <Statistic title="今日新增作品" value={overview.today_works} />
          </Card>
        </Col>
        <Col xs={8}>
          <Card className="soft-card" size="small">
            <Statistic title="今日新增存证" value={overview.today_certificates} />
          </Card>
        </Col>
        <Col xs={8}>
          <Card className="soft-card" size="small">
            <Statistic title="今日鉴定次数" value={overview.today_verifications} />
          </Card>
        </Col>
      </Row>

      {/* 趋势图 + 饼图 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={14}>
          <Card className="soft-card" title="近30天存证/验证趋势">
            {trend.length > 0 ? (
              <ReactECharts option={trendOption} style={{ height: 320 }} />
            ) : (
              <Empty description="暂无趋势数据" />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card className="soft-card" title="品类分布">
            {categories.length > 0 ? (
              <ReactECharts option={pieOption} style={{ height: 320 }} />
            ) : (
              <Empty description="暂无品类数据" />
            )}
          </Card>
        </Col>
      </Row>

      {/* 活跃传承人排行榜 */}
      <Card
        className="soft-card"
        title={
          <Space>
            <TrophyOutlined style={{ color: palette.gold }} />
            <span>活跃传承人 Top 5</span>
          </Space>
        }
      >
        <Table
          rowKey="user_id"
          columns={creatorColumns}
          dataSource={creators}
          pagination={false}
          size="middle"
        />
      </Card>
    </>
  );
}