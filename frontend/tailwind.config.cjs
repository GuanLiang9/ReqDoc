/** @type {import('tailwindcss').Config} */
// Colours and fonts mirror src/theme.ts (apple.com product-page style).
module.exports = {
  content: ['./src/**/*.{ts,tsx}'],
  // Ant Design ships its own reset, so Tailwind's preflight stays off to avoid fighting it.
  corePlugins: { preflight: false },
  theme: {
    extend: {
      colors: {
        canvas: '#F5F5F7',
        ink: '#1D1D1F',
        ink2: '#6E6E73',
        grey: '#86868B',
        hair: '#D2D2D7',
        blue: '#0071E3',
        'blue-link': '#0066CC',
        'blue-tint': '#E8F2FD',
        green: '#1D7A34',
        'green-tint': '#E8F5EC',
        orange: '#B64400',
        'orange-tint': '#FFF1E6',
        red: '#C4161C',
        'red-tint': '#FDECEC',
        // older names, now mapped to the new palette so existing classes keep working
        paper: '#F5F5F7',
        accent: '#0071E3',
        'accent-deep': '#0066CC',
        line: '#D2D2D7',
        'line-soft': '#E8E8ED',
        muted: '#6E6E73',
        sand: '#FFF1E6',
        sage: '#E8F5EC',
        rose: '#FDECEC',
        stone: '#F5F5F7',
      },
      fontFamily: {
        sans: ["-apple-system", 'BlinkMacSystemFont', "'SF Pro Text'", "'Inter'", "'Segoe UI'", 'sans-serif'],
      },
    },
  },
  plugins: [],
};
