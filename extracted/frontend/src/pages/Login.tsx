import { useState } from 'react'
import { api, setToken } from '../lib/api'
export default function Login({ onDone }: { onDone: () => void }) {
  const [u, setU] = useState(''), [p, setP] = useState(''), [err, setErr] = useState(''), [busy, setBusy] = useState(false)
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setErr('')
    try {
      const { data } = await api<{ token: string }>('/auth/login', { method: 'POST', json: { username: u, password: p } })
      setToken(data.token); onDone()
    } catch (x) { setErr((x as Error).message) } finally { setBusy(false) }
  }
  return (
    <form onSubmit={submit} className="mx-auto mt-24 flex max-w-sm flex-col gap-3 p-4">
      <h1 className="text-xl font-bold">ورود</h1>
      <input aria-label="نام کاربری" className="rounded border p-2" value={u} onChange={e => setU(e.target.value)} />
      <input aria-label="رمز عبور" type="password" className="rounded border p-2" value={p} onChange={e => setP(e.target.value)} />
      {err && <p role="alert" className="text-red-600">{err}</p>}
      <button disabled={busy || !u || !p} className="rounded bg-blue-600 p-2 text-white disabled:opacity-50">{busy ? '…' : 'ورود'}</button>
    </form>
  )
}
