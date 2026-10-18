import { faDigits, faMoney, jalali, fmtCell } from './fa'
test('digits', () => expect(faDigits('1405/07')).toBe('۱۴۰۵/۰۷'))
test('money', () => expect(faMoney(1250000)).toBe('۱,۲۵۰,۰۰۰'))
test('jalali', () => expect(jalali('2026-03-21T00:00:00Z')).toMatch(/^۱۴۰۵/))
test('fmtCell', () => {
  expect(fmtCell('bool', true)).toBe('بله')
  expect(fmtCell('money', null)).toBe('—')
  expect(fmtCell(undefined, 5)).toBe('۵')
})
