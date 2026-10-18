import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { FormDialog } from './FormDialog'
import { cleanValues } from './FieldInput'
const wrap = (ui: React.ReactElement) => render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>)
test('فیلد الزامی خالی ارسال نمی‌شود', async () => {
  const onSubmit = vi.fn()
  wrap(<FormDialog title="t" fields={[{ name: 'name', label: 'نام', required: true }]} onSubmit={onSubmit} onClose={() => {}} />)
  await userEvent.click(screen.getByRole('button', { name: 'ذخیره' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('الزامی')
  expect(onSubmit).not.toHaveBeenCalled()
})
test('ارسال و بستن', async () => {
  const onSubmit = vi.fn().mockResolvedValue(null), onClose = vi.fn()
  wrap(<FormDialog title="t" fields={[{ name: 'name', label: 'نام', required: true }, { name: 'n', label: 'عدد', type: 'number' }]} onSubmit={onSubmit} onClose={onClose} />)
  await userEvent.type(screen.getByLabelText(/نام/), 'x')
  await userEvent.type(screen.getByLabelText('عدد'), '5')
  await userEvent.click(screen.getByRole('button', { name: 'ذخیره' }))
  await vi.waitFor(() => expect(onClose).toHaveBeenCalled())
  expect(onSubmit).toHaveBeenCalledWith({ name: 'x', n: 5 })
})
test('cleanValues: خالی حذف، چک‌باکس بولی', () => {
  expect(cleanValues([{ name: 'a', label: 'a' }, { name: 'b', label: 'b', type: 'checkbox' }, { name: 'c', label: 'c', type: 'select', optionsFrom: { endpoint: '/x' } }], { a: '', c: '7' }))
    .toEqual({ b: false, c: 7 })
})
