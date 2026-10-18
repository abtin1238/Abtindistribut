import { useEffect, useState } from 'react'
import { api, setToken } from '../lib/api'
import { redirectToApp } from '../lib/roleApp'
import { Logo } from '../components/Icon'

type Status = { needs_setup: boolean; token_required: boolean }

async function signIn(username: string, password: string, onDone: () => void) {
  const { data } = await api<{ token: string; app?: string; home?: string }>('/auth/login', { method: 'POST', json: { username, password } })
  if (redirectToApp(data)) return
  setToken(data.token); onDone()
}

/** اولین اجرا: هیچ کاربری وجود ندارد؛ مدیر کل (بدون شعبه، سرپرست همهٔ شعب) همین‌جا تعریف می‌شود */
function Setup({ tokenRequired, onDone }: { tokenRequired: boolean; onDone: () => void }) {
  const [f, setF] = useState({ name: '', username: '', password: '', again: '', company_name: '', setup_token: '' })
  const [err, setErr] = useState(''), [busy, setBusy] = useState(false)
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF(s => ({ ...s, [k]: e.target.value }))
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setErr('')
    if (f.password !== f.again) return setErr('تکرار رمز با رمز یکسان نیست')
    setBusy(true)
    try {
      await api('/auth/setup', { method: 'POST', json: { name: f.name, username: f.username, password: f.password, company_name: f.company_name || null, setup_token: f.setup_token || null } })
      await signIn(f.username, f.password, onDone)
    } catch (x) { setErr((x as Error).message) } finally { setBusy(false) }
  }
  const ok = f.name && f.username && f.password && f.again && (!tokenRequired || f.setup_token)
  return (
    <div className="login">
      <form onSubmit={submit} className="box">
        <div className="logo-row"><Logo /><div><b>Abtin Distribution</b><small>راه‌اندازی اولیه</small></div></div>
        <h1>تعریف مدیر کل</h1>
        <p className="hint">مدیر کل به شعبه خاصی وصل نیست و همهٔ شعبه‌ها زیر نظر اوست.</p>
        <input aria-label="نام و نام خانوادگی" placeholder="نام و نام خانوادگی" value={f.name} onChange={set('name')} />
        <input aria-label="نام کاربری" placeholder="نام کاربری" value={f.username} onChange={set('username')} />
        <input aria-label="رمز عبور" placeholder="رمز عبور (حداقل ۸ نویسه؛ در production ۱۲)" type="password" value={f.password} onChange={set('password')} />
        <input aria-label="تکرار رمز" placeholder="تکرار رمز عبور" type="password" value={f.again} onChange={set('again')} />
        <input aria-label="نام شرکت" placeholder="نام شرکت (اختیاری)" value={f.company_name} onChange={set('company_name')} />
        {tokenRequired && <input aria-label="کد راه‌اندازی" placeholder="کد راه‌اندازی (SETUP_TOKEN)" type="password" value={f.setup_token} onChange={set('setup_token')} />}
        {err && <p role="alert" className="err">{err}</p>}
        <button disabled={busy || !ok}>{busy ? '…' : 'ساخت مدیر کل و ورود'}</button>
      </form>
    </div>
  )
}

export default function Login({ onDone }: { onDone: () => void }) {
  const [u, setU] = useState(''), [p, setP] = useState(''), [err, setErr] = useState(''), [busy, setBusy] = useState(false)
  const [st, setSt] = useState<Status | null>(null)
  useEffect(() => { api<Status>('/auth/setup-status').then(r => setSt(r.data)).catch(() => setSt({ needs_setup: false, token_required: false })) }, [])
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setErr('')
    try { await signIn(u, p, onDone) } catch (x) { setErr((x as Error).message) } finally { setBusy(false) }
  }
  if (st?.needs_setup) return <Setup tokenRequired={st.token_required} onDone={onDone} />
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
