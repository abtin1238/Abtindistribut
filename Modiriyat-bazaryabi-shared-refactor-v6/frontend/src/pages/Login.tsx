import { useState } from 'react'
import { api, setToken } from '../lib/api'
import { redirectToApp } from '../lib/roleApp'
import { Logo } from '../components/Icon'
export default function Login({ onDone }: { onDone: () => void }) {
  const [u, setU] = useState(''), [p, setP] = useState(''), [err, setErr] = useState(''), [busy, setBusy] = useState(false)
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setErr('')
    try {
      const { data } = await api<{ token: string; app?: string; home?: string }>('/auth/login', { method: 'POST', json: { username: u, password: p } })
      if (redirectToApp(data)) return
      setToken(data.token); onDone()
    } catch (x) { setErr((x as Error).message) } finally { setBusy(false) }
  }
  return (
    <div className="login">
      <form onSubmit={submit} className="box">
        <div className="logo-row"><Logo /><div><b>Abtin Distribution</b><small>مدیریت هوشمند پخش و توزیع</small></div></div>
        <h1>ورود</h1>
        <input aria-label="نام کاربری" placeholder="نام کاربری" value={u} onChange={e => setU(e.target.value)} />
        <input aria-label="رمز عبور" placeholder="رمز عبور" type="password" value={p} onChange={e => setP(e.target.value)} />
        {err && <p role="alert" className="err">{err}</p>}
        <button disabled={busy || !u || !p}>{busy ? '…' : 'ورود'}</button>
      </form>
    </div>
  )
}
