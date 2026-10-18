export type ThemeMode = 'dark' | 'light'
export function applyTheme(m: ThemeMode) {
  document.documentElement.dataset.theme = m
  try { localStorage.setItem('theme', m) } catch { /* حافظه در دسترس نیست */ }
}
export function currentTheme(): ThemeMode { return document.documentElement.dataset.theme === 'light' ? 'light' : 'dark' }
export function initTheme() {
  let s: string | null = null
  try { s = localStorage.getItem('theme') } catch { /* ignore */ }
  document.documentElement.dataset.theme = s === 'light' ? 'light' : 'dark'
}
