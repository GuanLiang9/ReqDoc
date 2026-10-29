import type { ThemeConfig } from 'antd';

/**
 * Design tokens in the apple.com product-page style: white and light-grey sections, near-black text,
 * one blue accent, pill buttons, soft rounded tiles, the system font. Keep this file and
 * tailwind.config.cjs in sync.
 */
export const colors = {
  canvas: '#F5F5F7',
  card: '#FFFFFF',
  ink: '#1D1D1F',
  ink2: '#6E6E73',
  grey: '#86868B',
  hair: '#D2D2D7',
  hairSoft: '#E8E8ED',
  blue: '#0071E3',
  blueHover: '#0077ED',
  blueActive: '#006EDB',
  blueLink: '#0066CC',
  blueTint: '#E8F2FD',
  green: '#1D7A34',
  greenTint: '#E8F5EC',
  orange: '#B64400',
  orangeTint: '#FFF1E6',
  red: '#C4161C',
  redTint: '#FDECEC',
} as const;

/** SF Pro on Apple devices; Inter (bundled) everywhere else. SF Pro itself cannot be redistributed. */
export const fontStack =
  "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'SF Pro Display', 'Inter', 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif";

const PILL = 980;

export const theme: ThemeConfig = {
  token: {
    colorPrimary: colors.blue,
    colorInfo: colors.blue,
    colorSuccess: colors.green,
    colorWarning: colors.orange,
    colorError: colors.red,
    colorLink: colors.blueLink,
    colorLinkHover: colors.blue,
    colorText: colors.ink,
    colorTextSecondary: colors.ink2,
    colorTextTertiary: colors.grey,
    colorBgLayout: colors.canvas,
    colorBgContainer: colors.card,
    colorBorder: colors.hair,
    colorBorderSecondary: colors.hairSoft,
    controlOutline: 'rgba(0, 113, 227, 0.25)',
    fontFamily: fontStack,
    fontSize: 14,
    borderRadius: 12,
    borderRadiusLG: 18,
    borderRadiusSM: 8,
    controlHeight: 40,
    wireframe: false,
  },
  components: {
    Button: {
      fontWeight: 400,
      primaryShadow: 'none',
      defaultShadow: 'none',
      dangerShadow: 'none',
      borderRadius: PILL,
      borderRadiusLG: PILL,
      borderRadiusSM: PILL,
      paddingInline: 22,
      defaultBg: 'transparent',
      defaultColor: colors.blue,
      defaultBorderColor: colors.blue,
      defaultHoverBg: colors.blueTint,
      defaultHoverColor: colors.blue,
      defaultHoverBorderColor: colors.blue,
      defaultActiveBg: '#D6E8FB',
      defaultActiveColor: colors.blue,
      defaultActiveBorderColor: colors.blue,
      colorPrimaryHover: colors.blueHover,
      colorPrimaryActive: colors.blueActive,
    },
    Tabs: {
      inkBarColor: 'transparent',
      itemSelectedColor: colors.ink,
      itemHoverColor: colors.ink,
      itemActiveColor: colors.ink,
      itemColor: colors.ink2,
      titleFontSize: 14,
      horizontalMargin: '0 0 28px 0',
    },
    Table: {
      headerBg: 'transparent',
      headerColor: colors.grey,
      headerSplitColor: 'transparent',
      borderColor: colors.hairSoft,
      rowHoverBg: '#FAFAFC',
      cellPaddingBlock: 16,
      cellPaddingBlockSM: 10,
      cellPaddingInlineSM: 10,
    },
    Card: { borderRadiusLG: 18, headerFontSize: 14, colorBorderSecondary: colors.hairSoft },
    Modal: { borderRadiusLG: 22, titleFontSize: 24 },
    Drawer: { borderRadiusLG: 0 },
    Progress: { defaultColor: colors.blue, remainingColor: colors.hairSoft },
    Segmented: {
      trackBg: colors.hairSoft,
      itemSelectedBg: colors.card,
      itemSelectedColor: colors.ink,
      itemColor: colors.ink2,
    },
    Select: { optionSelectedBg: colors.blueTint, optionSelectedColor: colors.ink },
    Input: { activeBorderColor: colors.blue, hoverBorderColor: colors.grey, activeShadow: '0 0 0 4px rgba(0,113,227,0.18)' },
    DatePicker: { activeBorderColor: colors.blue, activeShadow: '0 0 0 4px rgba(0,113,227,0.18)' },
    Alert: { borderRadiusLG: 14 },
    Steps: { colorPrimary: colors.blue },
    Badge: { colorError: colors.blue },
    Dropdown: { borderRadiusLG: 14 },
  },
};
