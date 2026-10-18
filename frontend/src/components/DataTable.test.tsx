import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DataTable } from './DataTable'
const cols = [{ key: 'name', label: 'نام' }, { key: 'amount', label: 'مبلغ', kind: 'money' as const }]
const wrap = (ui: React.ReactElement) => render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>)
test('حالت‌های loading/error/empty', () => {
  const { rerender } = wrap(<DataTable columns={cols} rows={[]} loading />)
  expect(screen.getByRole('status')).toBeInTheDocument()
  rerender(<QueryClientProvider client={new QueryClient()}><DataTable columns={cols} rows={[]} error={new Error('بد')} /></QueryClientProvider>)
  expect(screen.getByRole('alert')).toHaveTextContent('بد')
  rerender(<QueryClientProvider client={new QueryClient()}><DataTable columns={cols} rows={[]} empty="خالی" /></QueryClientProvider>)
  expect(screen.getByText('خالی')).toBeInTheDocument()
})
test('نمایش ارقام فارسی و مرتب‌سازی', async () => {
  wrap(<DataTable columns={cols} rows={[{ id: 1, name: 'ب', amount: 2000 }, { id: 2, name: 'الف', amount: 1000 }]} />)
  expect(screen.getByText('۲,۰۰۰')).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'نام' }))
  const cells = screen.getAllByRole('row').slice(1).map(r => r.textContent)
  expect(cells[0]).toContain('الف')
})
test('XSS: متن به‌صورت متن رندر می‌شود', () => {
  wrap(<DataTable columns={cols} rows={[{ id: 1, name: '<img src=x onerror=alert(1)>', amount: 1 }]} />)
  expect(document.querySelector('img')).toBeNull()
})
