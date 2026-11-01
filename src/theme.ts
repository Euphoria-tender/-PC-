/**
 * 文化DNA —— 国风设计系统（配色 / 主题令牌）
 * 调性：宣纸为底、印章为点睛、墨色为骨、鎏金为饰，克制优雅。
 */
import type { ThemeConfig } from 'antd';

/** 全局色板（供 ECharts / 内联样式 / 共享组件使用） */
export const palette = {
  cinnabar: '#A8432F',      // 印章红 / 朱砂 —— 主色
  cinnabarDeep: '#7E2F20',
  cinnabarLight: '#F3E4DD', // 印章红淡底（选中态）
  gold: '#B98A4F',          // 鎏金 —— 点缀 / 排名 / 存证
  ink: '#2C251E',           // 墨色 —— 主文字
  inkSecondary: '#7A6F63',  // 墨灰 —— 次文字
  inkTertiary: '#A79C8C',   // 淡墨 —— 弱化文字
  paper: '#F3EEE3',         // 宣纸 —— 布局背景
  paperCard: '#FFFEFB',     // 卡片底（暖白）
  border: '#E6DCC9',        // 暖色描边
  borderLight: '#EFE8DA',
  celadon: '#5E8B83',       // 青瓷 —— 辅助
  success: '#4E8A5F',       // 青绿 —— 成功
  warning: '#C08B3A',       // 金 —— 警告
  error: '#B8422F',         // 朱 —— 错误
};

/** 展示字体（标题 / 品牌 / 印章）：宋体系，Windows 回退 SimSun */
export const FONT_SERIF =
  "'Noto Serif SC','Source Han Serif SC','Songti SC','STSong','SimSun',serif";

/** 正文字体：雅黑系 */
export const FONT_SANS =
  "'PingFang SC','Microsoft YaHei','Segoe UI',-apple-system,BlinkMacSystemFont,sans-serif";

/** Ant Design ConfigProvider 主题配置 */
export const themeConfig: ThemeConfig = {
  token: {
    colorPrimary: palette.cinnabar,
    colorInfo: palette.celadon,
    colorSuccess: palette.success,
    colorWarning: palette.warning,
    colorError: palette.error,
    colorLink: palette.cinnabar,
    colorTextBase: palette.ink,
    colorText: palette.ink,
    colorTextSecondary: palette.inkSecondary,
    colorTextTertiary: palette.inkTertiary,
    colorBgLayout: palette.paper,
    colorBgContainer: palette.paperCard,
    colorBorder: palette.border,
    colorBorderSecondary: palette.borderLight,
    borderRadius: 10,
    fontFamily: FONT_SANS,
    fontSize: 14,
    controlHeight: 36,
  },
  components: {
    Layout: {
      headerBg: palette.paperCard,
      bodyBg: palette.paper,
      siderBg: palette.paperCard,
    },
    Card: {
      colorBgContainer: palette.paperCard,
      headerFontSize: 16,
      headerFontSizeSM: 15,
    },
    Table: {
      headerBg: '#FAF6EC',
      headerColor: palette.inkSecondary,
      headerSplitColor: 'transparent',
    },
    Menu: {
      itemSelectedBg: palette.cinnabarLight,
      itemSelectedColor: palette.cinnabar,
      itemBorderRadius: 8,
    },
    Button: {
      borderRadius: 8,
    },
    Tag: {
      borderRadiusSM: 4,
    },
  },
};