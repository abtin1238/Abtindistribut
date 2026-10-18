const D = '۰۱۲۳۴۵۶۷۸۹'
export const faDigits = (v: string | number) => String(v).replace(/\d/g, d => D[+d])
export const faMoney = (v: number | string) => faDigits(Number(v).toLocaleString('en-US'))
export const jalali = (iso: string) =>
  new Intl.DateTimeFormat('fa-IR-u-ca-persian', { year: 'numeric', month: '2-digit', day: '2-digit', timeZone: 'UTC' }).format(new Date(iso))
export function fmtCell(kind: string | undefined, v: unknown): string {
  if (v === null || v === undefined || v === '') return '—'
  switch (kind) {
    case 'money': return faMoney(v as number)
    case 'num': return faDigits(v as number)
    case 'date': { const d = new Date(String(v)); return isNaN(+d) ? String(v) : jalali(d.toISOString()) }
    case 'bool': return v ? 'بله' : 'خیر'
    default: return typeof v === 'number' ? faDigits(v) : String(v)
  }
}
/** عدد فشرده: میلیارد/میلیون برای کارت‌های مدیریتی */
export function faCompact(v: number | string | null | undefined): { n: string; unit: string } {
  const x = Number(v ?? 0), a = Math.abs(x)
  const f = (y: number) => faDigits(y.toLocaleString('en-US', { maximumFractionDigits: 1 }))
  return a >= 1e9 ? { n: f(x / 1e9), unit: 'میلیارد' } : a >= 1e6 ? { n: f(x / 1e6), unit: 'میلیون' } : { n: f(x), unit: '' }
}
export const faPct = (v: number | string | null | undefined) =>
  v == null || v === '' ? '—' : `${faDigits(Number(v).toLocaleString('en-US', { maximumFractionDigits: 1 }))}٪`
/** تاریخ شمسی کوتاه (ماه و روز) از ISO */
export const jalaliMD = (iso: string) => {
  const d = new Date(`${String(iso).slice(0, 10)}T12:00:00Z`)
  return isNaN(+d) ? String(iso) : new Intl.DateTimeFormat('fa-IR-u-ca-persian', { month: 'short', day: 'numeric', timeZone: 'UTC' }).format(d)
}
export const jalaliFull = (iso?: string | null) => {
  if (!iso) return '—'
  const d = new Date(`${String(iso).slice(0, 10)}T12:00:00Z`)
  return isNaN(+d) ? String(iso) : new Intl.DateTimeFormat('fa-IR-u-ca-persian', { year: 'numeric', month: '2-digit', day: '2-digit', timeZone: 'UTC' }).format(d)
}
