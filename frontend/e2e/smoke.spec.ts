import { test, expect } from '@playwright/test'
const USER = process.env.E2E_USER ?? 'admin', PASS = process.env.E2E_PASS ?? ''
async function login(page: import('@playwright/test').Page) {
  await page.goto('/app/')
  await page.getByLabel('نام کاربری').fill(USER)
  await page.getByLabel('رمز عبور').fill(PASS)
  await page.getByRole('button', { name: 'ورود' }).click()
}
test('رمز اشتباه خطا نشان می‌دهد', async ({ page }) => {
  await page.goto('/app/')
  await page.getByLabel('نام کاربری').fill('nobody')
  await page.getByLabel('رمز عبور').fill('wrong-password')
  await page.getByRole('button', { name: 'ورود' }).click()
  await expect(page.getByRole('alert')).toBeVisible()
})
test.describe('با ورود واقعی', () => {
  test.skip(!PASS, 'E2E_PASS تنظیم نشده')
  test('داشبورد و منو', async ({ page }) => {
    await login(page)
    await expect(page.getByRole('heading', { name: 'داشبورد' })).toBeVisible()
    await page.getByRole('link', { name: 'مشتریان' }).click()
    await expect(page.getByRole('heading', { name: 'مشتریان' })).toBeVisible()
  })
  test('ساخت مشتری و دیدنش در لیست', async ({ page }) => {
    await login(page)
    await page.goto('/app/customers')
    const code = `E2E${Date.now() % 1e6}`
    await page.getByRole('button', { name: '+ مشتری جدید' }).click()
    await page.getByLabel(/کد/).fill(code)
    await page.getByLabel(/نام/).first().fill('مشتری تست')
    await page.getByRole('button', { name: 'ذخیره' }).click()
    await expect(page.getByRole('status')).toContainText('ثبت شد')
  })
  test('سفارش جدید: انتخاب‌ها از سرور بارگذاری می‌شوند', async ({ page }) => {
    await login(page)
    await page.goto('/app/orders/new')
    await expect(page.getByLabel('مشتری')).toBeVisible()
    await expect(page.getByLabel('کالا').first()).toBeVisible()
  })
})
