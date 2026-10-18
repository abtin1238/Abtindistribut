import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import StockCountDetail from './StockCountDetail'
import BankReconcile from './BankReconcile'
import JournalTemplates from './JournalTemplates'

const json = (b: unknown) => new Response(JSON.stringify(b), { status: 200 })
function mockApi(routes: Record<string, unknown>) {
  const calls: { url: string; method: string; body?: any }[] = []
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    const path = String(url).replace(/^\/api/, '')
    calls.push({ url: path, method: init?.method ?? 'GET', body: init?.body ? JSON.parse(String(init.body)) : undefined })
    for (const k of Object.keys(routes)) if (path === k) return json(routes[k])
    return json({})
  }))
  return calls
}
const wrap = (ui: React.ReactNode, at = '/') => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[at]}>{ui}</MemoryRouter></QueryClientProvider>)
afterEach(() => vi.restoreAllMocks())

test('انبارگردانی: اختلاف زنده و ذخیره‌ی شمارش', async () => {
  const calls = mockApi({ '/stock/counts/7': { id: 7, number: 'CNT-1', status: 'counting', note: '', counted_lines: 0, total_value_difference: 0, lines: [{ product_id: 3, product: 'کالا-الف', sku: 'A', system_qty: 10, counted_qty: null, avg_cost: 50 }] } })
  wrap(<Routes><Route path="/stock-counts/:id" element={<StockCountDetail />} /></Routes>, '/stock-counts/7')
  const inp = await screen.findByLabelText('شمارش کالا-الف')
  await userEvent.type(inp, '7')
  const row = screen.getByText('کالا-الف').closest('tr')!
  expect(within(row).getByText(/۳/)).toBeInTheDocument()            // اختلاف ۷−۱۰
  expect(screen.getByRole('button', { name: 'تأیید و اعمال اختلاف‌ها' })).toBeDisabled()   // تا ذخیره‌ی شمارش
  await userEvent.click(screen.getByRole('button', { name: 'ذخیره شمارش' }))
  await vi.waitFor(() => expect(calls.find(c => c.method === 'PUT')?.body).toEqual({ lines: [{ product_id: 3, counted_qty: 7 }] }))
})

test('مغایرت‌گیری: اختلاف با مانده‌ی صورت‌حساب و ارسال سطرهای انتخابی', async () => {
  const calls = mockApi({
    '/bank-accounts': [{ id: 1, name: 'ملت' }],
    '/bank-accounts/1/reconcile': { book_balance: 1030, cleared_balance: 0, in_transit_deposits: 50, outstanding_payments: 0, lines: [{ line_id: 11, number: 'JE-1', date: '2026-10-01', description: 'افتتاحیه', debit: 1000, credit: 0 }, { line_id: 12, number: 'JE-2', date: '2026-10-02', description: 'کارمزد', debit: 0, credit: 20 }] },
    '/bank-accounts/1/reconciliations': [],
  })
  wrap(<BankReconcile />)
  await userEvent.selectOptions(await screen.findByLabelText('حساب بانکی'), '1')
  await userEvent.click(await screen.findByLabelText('تطبیق JE-1'))
  await userEvent.click(screen.getByLabelText('تطبیق JE-2'))
  await userEvent.type(screen.getByRole('spinbutton'), '980')
  expect(await screen.findByText(/متعادل/)).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'ثبت مغایرت‌گیری' }))
  await vi.waitFor(() => expect(calls.find(c => c.method === 'POST')?.body).toMatchObject({ statement_balance: 980, line_ids: [11, 12] }))
})

test('قالب سندسازی: ذخیره فقط وقتی ضرایب متعادل است', async () => {
  mockApi({ '/journal-templates': [], '/accounts': [{ id: 1, code: '5300', name: 'هزینه', level: 3, active: true }, { id: 2, code: '1110', name: 'صندوق', level: 3, active: true }] })
  wrap(<JournalTemplates />)
  await userEvent.type(await screen.findByLabelText('نام قالب'), 'اجاره')
  await userEvent.selectOptions(screen.getByLabelText('حساب 1'), '5300')
  await userEvent.selectOptions(screen.getByLabelText('حساب 2'), '1110')
  await userEvent.selectOptions(screen.getByLabelText('سمت 2'), 'credit')
  const save = screen.getByRole('button', { name: 'ذخیره قالب' })
  expect(save).toBeEnabled()
  await userEvent.clear(screen.getByLabelText('ضریب 2')); await userEvent.type(screen.getByLabelText('ضریب 2'), '2')
  expect(save).toBeDisabled()
  expect(screen.getByText(/باید برابر باشد/)).toBeInTheDocument()
})
