/** مقصد drill-down که بک‌اند در کارت‌های داشبورد/مدیرعامل می‌فرستد: صفحه، گزارش یا دفتر کل */
export type Drill = { page?: string; report?: string; params?: Record<string, string> }
/** نام صفحه‌های قدیمی بک‌اند ← مسیر React */
const PAGE_ROUTE: Record<string, string> = { treasury: 'checks', accounting: 'journal', hr: 'employees', stock: 'stock', orders: 'orders', customers: 'customers' }
export function drillTarget(d: Drill | undefined | null): { kind: 'route'; to: string } | { kind: 'ledger'; code: string } | null {
  if (!d) return null
  if (d.page) return { kind: 'route', to: `/${PAGE_ROUTE[d.page] ?? d.page}` }
  if (d.report === 'general-ledger') return d.params?.account_code ? { kind: 'ledger', code: d.params.account_code } : null
  if (d.report) return { kind: 'route', to: `/reports?${new URLSearchParams({ name: d.report, ...(d.params ?? {}) }).toString()}` }
  return null
}
