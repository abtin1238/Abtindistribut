/** کاربران ویزیتور و مأمور پخش به اپ موبایل خودشان می‌روند، نه پنل مدیریتی (همان رفتار app.js قدیمی). */
const APP_TOKEN_KEY: Record<string, string> = { visitor: 'vtoken', driver: 'dtoken' }
export function redirectToApp(d: { token: string; app?: string; home?: string }): boolean {
  const key = d.app ? APP_TOKEN_KEY[d.app] : undefined
  if (!key || !d.home || !/^\/(?![\/\\])/.test(d.home)) return false
  localStorage.setItem(key, d.token)
  location.replace(d.home)
  return true
}
