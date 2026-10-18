import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Login from './Login'
afterEach(() => vi.restoreAllMocks())
test('نمایش خطای سرور', async () => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation(async () => new Response(JSON.stringify({ message: 'نام کاربری یا رمز عبور نادرست است' }), { status: 401 })))
  render(<Login onDone={() => {}} />)
  await userEvent.type(screen.getByLabelText('نام کاربری'), 'a')
  await userEvent.type(screen.getByLabelText('رمز عبور'), 'b')
  await userEvent.click(screen.getByRole('button', { name: 'ورود' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('نادرست')
})
test('موفقیت onDone را صدا می‌زند', async () => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation(async () => new Response(JSON.stringify({ token: 't', needs_setup: false }), { status: 200 })))
  const done = vi.fn()
  render(<Login onDone={done} />)
  await userEvent.type(screen.getByLabelText('نام کاربری'), 'a')
  await userEvent.type(screen.getByLabelText('رمز عبور'), 'b')
  await userEvent.click(screen.getByRole('button', { name: 'ورود' }))
  await vi.waitFor(() => expect(done).toHaveBeenCalled())
})
