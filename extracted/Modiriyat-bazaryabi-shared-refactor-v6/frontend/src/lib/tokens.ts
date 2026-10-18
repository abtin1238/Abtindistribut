import { applyTheme } from './theme'
export type ThemeCfg = { color: string; radius: number; font_scale: number; mode: 'system' | 'dark' | 'light' }
const HEX = /^#[0-9a-fA-F]{6}$/
const ID = 'abtin-tokens'
/** رنگ برند، گردی گوشه‌ها و اندازهٔ متن را به‌صورت CSS variable روی :root می‌نویسد (همان رفتار پنل قدیمی). */
export function applyTokens(t: Partial<ThemeCfg> | null | undefined) {
  if (!t) return
  const c = t.color && HEX.test(t.color) ? t.color : '#2f7bff'
  let el = document.getElementById(ID) as HTMLStyleElement | null
  if (!el) { el = document.createElement('style'); el.id = ID; document.head.appendChild(el) }
  el.textContent = `:root:root:root{--bl:${c};--brand:${c};--bl2:color-mix(in srgb,${c} 72%,#fff);--btn:linear-gradient(180deg,color-mix(in srgb,${c} 88%,#fff),color-mix(in srgb,${c} 86%,#000));--r:${t.radius ?? 16}px}html{font-size:${t.font_scale ?? 100}%}`
}
/** حالت پیش‌فرض تم فقط وقتی اعمال می‌شود که کاربر خودش تم را دستی انتخاب نکرده باشد. */
export function applyDefaultMode(mode: ThemeCfg['mode'] | undefined) {
  let own: string | null = null
  try { own = localStorage.getItem('theme') } catch { /* ignore */ }
  if (own || !mode || mode === 'system') return
  document.documentElement.dataset.theme = mode
}
export { applyTheme }
