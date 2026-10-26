import type { ThemeConfig } from 'antd';

/**
 * Design tokens, taken from the design-website skill (buildinamsterdam.com style):
 * off-white paper, black ink, white cards, terracotta accent, hairline borders, Inter + Cormorant Garamond.
 * Keep this file and tailwind.config.cjs in sync.
 */
export const colors = {
  paper: '#F2EFE6',
  ink: '#231F20',
  black: '#000000',
  accent: '#C38133', // decorative only: about 3:1 on white
  accentDeep: '#8F5A1E', // links and small text: passes contrast on white and paper
  muted: '#6B6660',
  grey: '#999999',
  line: '#DDD9CE',
  lineSoft: '#ECE8DC',
  card: '#FFFFFF',
  sage: '#E7EEE3',
  sageInk: '#2F5D3A',
  sand: '#F6EADB',
  sandInk: '#7A4A12',
  rose: '#F6E4E1',
  roseInk: '#8A2F25',
  stone: '#ECE8DE',
} as const;

export const fontStack =
  "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif";
export const serifStack = "'Cormorant Garamond', Georgia, 'Times New Roman', serif";

export const theme: ThemeConfig = {
  token: {
    colorPrimary: colors.ink,
    colorInfo: colors.ink,
    colorSuccess: colors.sageInk,
    colorWarning: colors.accentDeep,
    colorError: '#A8362B',
    colorLink: colors.accentDeep,
    colorLinkHover: colors.accent,
    colorText: colors.ink,
    colorTextSecondary: colors.muted,
    colorTextTertiary: colors.grey,
    colorBgLayout: colors.paper,
    colorBgContainer: colors.card,
    colorBorder: colors.line,
    colorBorderSecondary: colors.lineSoft,
    controlOutline: 'rgba(195, 129, 51, 0.22)',
    fontFamily: fontStack,
    fontSize: 14,
    borderRadius: 10,
    borderRadiusLG: 16,
    controlHeight: 38,
    wireframe: false,
  },
  components: {
    Button: {
      fontWeight: 600,
      primaryShadow: 'none',
      defaultShadow: 'none',
      dangerShadow: 'none',
      defaultBorderColor: colors.ink,
      defaultColor: colors.ink,
      defaultHoverBg: colors.ink,
      defaultHoverColor: colors.paper,
      defaultHoverBorderColor: colors.ink,
      defaultActiveBg: colors.black,
      defaultActiveColor: colors.paper,
      defaultActiveBorderColor: colors.black,
      colorPrimaryHover: colors.black,
      colorPrimaryActive: colors.black,
      paddingInline: 20,
    },
    Tabs: {
      inkBarColor: colors.accent,
      itemSelectedColor: colors.ink,
      itemHoverColor: colors.ink,
      itemActiveColor: colors.ink,
      itemColor: colors.muted,
      titleFontSize: 14,
      horizontalMargin: '0 0 20px 0',
      horizontalItemGutter: 32,
    },
    Table: {
      headerBg: 'transparent',
      headerColor: colors.muted,
      headerSplitColor: 'transparent',
      borderColor: colors.lineSoft,
      rowHoverBg: '#FAF8F2',
      cellPaddingBlock: 16,
      cellPaddingBlockSM: 10,
      cellPaddingInlineSM: 10,
    },
    Card: { borderRadiusLG: 16, headerFontSize: 14, colorBorderSecondary: colors.line },
    Modal: { borderRadiusLG: 18, titleFontSize: 20 },
    Drawer: { borderRadiusLG: 0 },
    Progress: { defaultColor: colors.accent, remainingColor: colors.lineSoft },
    Segmented: {
      trackBg: '#E8E3D5',
      itemSelectedBg: colors.ink,
      itemSelectedColor: colors.paper,
      itemColor: colors.muted,
    },
    Select: { optionSelectedBg: colors.sand, optionSelectedColor: colors.ink },
    Input: { activeBorderColor: colors.accent, hoverBorderColor: colors.ink, activeShadow: '0 0 0 3px rgba(195,129,51,0.18)' },
    Alert: { borderRadiusLG: 12 },
    Steps: { colorPrimary: colors.ink },
    Badge: { colorError: colors.accentDeep },
    Dropdown: { borderRadiusLG: 12 },
  },
};
