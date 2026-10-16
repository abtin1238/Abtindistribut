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
