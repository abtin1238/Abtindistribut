/** برچسب فارسی رویدادهای حسابرسی (همان فهرست پنل قدیمی + رویدادهایی که بک‌اند جدید ثبت می‌کند) */
export const AUDIT_ACT: Record<string, string> = {
  create: 'ثبت', update: 'ویرایش', delete: 'حذف', login: 'ورود', logout: 'خروج', logout_all: 'خروج از همهٔ نشست‌ها', approve: 'تأیید', reject: 'رد',
  cancel: 'لغو', reverse: 'برگشت', close: 'بستن', reopen: 'بازگشایی', post: 'ثبت قطعی', pay: 'پرداخت', receive: 'دریافت', return: 'مرجوعی', assign: 'تخصیص',
  payment: 'پرداخت/دریافت', stock_adjust: 'اصلاح موجودی', delivery_update: 'به‌روزرسانی مأموریت', upload: 'آپلود', download: 'دانلود',
  password_change: 'تغییر رمز', password_reset: 'بازنشانی رمز', switch_company: 'تغییر شرکت', refresh_reuse_detected: 'استفادهٔ مجدد از توکن',
  import: 'ورود اطلاعات', export: 'خروجی گزارش', export_job: 'خروجی پس‌زمینه',
}
export const AUDIT_ENT: Record<string, string> = {
  user: 'کاربر', role: 'نقش', membership: 'عضویت', company: 'شرکت', branch: 'شعبه', supplier: 'تأمین‌کننده', warehouse: 'انبار', order: 'سفارش', customer: 'مشتری',
  customer_address: 'نشانی مشتری', product: 'کالا', stock: 'موجودی', payment: 'پرداخت', delivery: 'مأموریت', document: 'سند', journal: 'سند حسابداری',
  price_rule: 'قاعدهٔ قیمت', purchase: 'خرید', check: 'چک', visit: 'ویزیت', invoice: 'فاکتور', contract: 'قرارداد', employee: 'کارمند', shift: 'شیفت',
  geofence: 'ناحیه', report: 'گزارش',
}
export const auditAct = (a: unknown) => AUDIT_ACT[String(a)] ?? String(a ?? '—')
export const auditEnt = (e: unknown) => AUDIT_ENT[String(e)] ?? String(e ?? '—')
/** زمان حسابرسی با ساعت؛ مقدار بدون منطقهٔ زمانی UTC فرض می‌شود */
export function auditTime(v: unknown): string {
  if (!v) return '—'
  const s = String(v), d = new Date(/Z|[+-]\d\d:?\d\d$/.test(s) ? s : `${s}Z`)
  return isNaN(+d) ? s : new Intl.DateTimeFormat('fa-IR-u-ca-persian', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(d)
}
