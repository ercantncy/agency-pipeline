const v = (n) => `rgb(var(--${n}) / <alpha-value>)`;
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      fontFamily: { sans: ['"Inter Variable"', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'] },
      colors: {
        bg: v('bg'), surface: v('surface'), subtle: v('subtle'), line: v('line'), 'line-strong': v('line-strong'),
        ink: v('ink'), 'ink-2': v('ink-2'), 'ink-3': v('ink-3'),
        accent: v('accent'), 'accent-fg': v('accent-fg'),
        good: v('good'), warn: v('warn'), crit: v('crit'),
      },
      fontSize: { '2xs': ['11px', '16px'], xs: ['12px', '16px'], sm: ['13px', '20px'], base: ['14px', '22px'] },
      borderRadius: { DEFAULT: '6px', lg: '8px', xl: '12px' },
    },
  },
  plugins: [],
};
