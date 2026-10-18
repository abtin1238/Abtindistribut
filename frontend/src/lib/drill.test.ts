import { drillTarget } from './drill'
test('drill به گزارش با پارامترها، دفتر کل و صفحهٔ قدیمی نگاشت می‌شود', () => {
  expect(drillTarget({ report: 'sales', params: { by: 'day', start: '2026-10-01' } })).toEqual({ kind: 'route', to: '/reports?name=sales&by=day&start=2026-10-01' })
  expect(drillTarget({ report: 'general-ledger', params: { account_code: '1101' } })).toEqual({ kind: 'ledger', code: '1101' })
  expect(drillTarget({ page: 'treasury' })).toEqual({ kind: 'route', to: '/checks' })
  expect(drillTarget(undefined)).toBeNull(); expect(drillTarget({ report: 'general-ledger' })).toBeNull()
})
