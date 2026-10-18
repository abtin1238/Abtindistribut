import { resources } from './resources'
import { navGroups } from '../nav'
test('مسیرها یکتا و ستون‌ها تعریف‌شده‌اند', () => {
  const paths = resources.map(r => r.path)
  expect(new Set(paths).size).toBe(paths.length)
  for (const r of resources) { expect(r.columns.length).toBeGreaterThan(0); expect(r.endpoint.startsWith('/')).toBe(true) }
})
test('هر آیتم منو مقصد دارد', () => {
  const known = new Set([...resources.map(r => r.path), 'dashboard', 'ceo', 'reports', 'settings', 'orders/new', 'purchases/new', 'journal/new', 'proposals/new', 'stock-reports', 'bank-reconcile', 'accounts-tree', 'journal-templates', 'search', 'notifications', 'import', 'organizations', 'funnel', 'map'])
  for (const g of navGroups) for (const i of g.items) expect(known.has(i.to)).toBe(true)
})
test('هیچ فیلد انتخابی بدون منبع گزینه نیست', () => {
  for (const r of resources) for (const f of [...(r.create?.fields ?? []), ...(r.actions ?? []).flatMap(a => a.fields ?? [])])
    if (f.type === 'select' || f.type === 'multi') expect(f.options || f.optionsFrom).toBeTruthy()
})
