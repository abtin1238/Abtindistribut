import { redirectToApp } from './roleApp'
afterEach(() => { vi.unstubAllGlobals(); localStorage.clear() })
test('ویزیتور به اپ خودش هدایت می‌شود و توکن اپ ذخیره می‌شود', () => {
  const replace = vi.fn(); vi.stubGlobal('location', { replace })
  expect(redirectToApp({ token: 'T', app: 'visitor', home: '/mobile/visitor/' })).toBe(true)
  expect(localStorage.getItem('vtoken')).toBe('T'); expect(replace).toHaveBeenCalledWith('/mobile/visitor/')
})
test('مأمور پخش توکن dtoken می‌گیرد', () => {
  vi.stubGlobal('location', { replace: vi.fn() })
  expect(redirectToApp({ token: 'D', app: 'driver', home: '/mobile/driver/' })).toBe(true)
  expect(localStorage.getItem('dtoken')).toBe('D')
})
test('کاربر پنل در همین اپ می‌ماند', () => {
  const replace = vi.fn(); vi.stubGlobal('location', { replace })
  expect(redirectToApp({ token: 'P', app: 'panel', home: '/web/' })).toBe(false)
  expect(replace).not.toHaveBeenCalled(); expect(localStorage.getItem('vtoken')).toBeNull()
})
test('مقصد خارج از سایت پذیرفته نمی‌شود', () => {
  const replace = vi.fn(); vi.stubGlobal('location', { replace })
  expect(redirectToApp({ token: 'X', app: 'visitor', home: 'https://evil.example/' })).toBe(false)
  expect(replace).not.toHaveBeenCalled()
})
test('مقصد protocol-relative هم رد می‌شود', () => {
  const replace = vi.fn(); vi.stubGlobal('location', { replace })
  expect(redirectToApp({ token: 'X', app: 'driver', home: '//evil.example/' })).toBe(false)
  expect(replace).not.toHaveBeenCalled()
})
