import { auditAct, auditEnt, auditTime } from './auditLabels'
test('برچسب فارسی و بازگشت به مقدار خام برای کلید ناشناخته', () => {
  expect(auditAct('create')).toBe('ثبت'); expect(auditEnt('customer')).toBe('مشتری')
  expect(auditAct('something_new')).toBe('something_new'); expect(auditEnt(null)).toBe('—')
})
test('زمان بدون منطقه UTC فرض می‌شود و مقدار نامعتبر دست‌نخورده می‌ماند', () => {
  expect(auditTime('2026-10-18T10:00:00')).toBe(auditTime('2026-10-18T10:00:00Z'))
  expect(auditTime('نامعتبر')).toBe('نامعتبر'); expect(auditTime(null)).toBe('—')
})
