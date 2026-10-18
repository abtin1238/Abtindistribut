// رنگ‌ها از توکن‌های دیزاین‌سیستم (src/styles/palette.css) می‌آیند تا Tailwind و پنل قدیمی یک ظاهر داشته باشند.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        card: 'var(--card)', bd: 'var(--bd)', tx: 'var(--tx)', mut: 'var(--mut)', bg0: 'var(--bg0)',
        bl: 'var(--bl)', ok: 'var(--ok)', bad: 'var(--bad)', warn: 'var(--warn)', pur: 'var(--pur)',
        ctl: 'var(--ctl-bg)',
        'ok-soft': 'color-mix(in srgb,var(--ok) 14%,transparent)',
        'bad-soft': 'color-mix(in srgb,var(--bad) 14%,transparent)',
        'warn-soft': 'color-mix(in srgb,var(--warn) 14%,transparent)',
        'bl-soft': 'color-mix(in srgb,var(--bl) 14%,transparent)',
      },
      borderColor: { DEFAULT: 'var(--bd)' },
      borderRadius: { ds: 'var(--r)', 'ds-sm': 'var(--r-sm)' },
    },
  },
  plugins: [],
}
