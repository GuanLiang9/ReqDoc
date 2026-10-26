/** @type {import('tailwindcss').Config} */
// Colours and fonts mirror src/theme.ts (the design-website skill palette).
module.exports = {
  content: ['./src/**/*.{ts,tsx}'],
  // Ant Design ships its own reset, so Tailwind's preflight stays off to avoid fighting it.
  corePlugins: { preflight: false },
  theme: {
    extend: {
      colors: {
        paper: '#F2EFE6',
        ink: '#231F20',
        accent: '#C38133',
        'accent-deep': '#8F5A1E',
        line: '#DDD9CE',
        'line-soft': '#ECE8DC',
        muted: '#6B6660',
        sand: '#F6EADB',
        sage: '#E7EEE3',
        rose: '#F6E4E1',
        stone: '#ECE8DE',
      },
      fontFamily: {
        sans: ["'Inter'", 'system-ui', 'sans-serif'],
        serif: ["'Cormorant Garamond'", 'Georgia', 'serif'],
      },
    },
  },
  plugins: [],
};
