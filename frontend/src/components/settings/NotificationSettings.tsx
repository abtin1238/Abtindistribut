import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { get, send } from '../../lib/api'
import { faDigits } from '../../lib/fa'
import { Btn, Card, ErrorBox, Spinner } from '../ui'

type Events = { channels: { code: string; label: string; available: boolean }[]; events: { code: string; title: string }[] }
type Prefs = { prefs: Record<string, Record<string, boolean>>; contact: { email: string; phone: string }; push_subscriptions: number }

const fromB64Url = (s: string) => {
  const raw = atob((s + '='.repeat((4 - (s.length % 4)) % 4)).replace(/-/g, '+').replace(/_/g, '/'))
  return Uint8Array.from(raw, c => c.charCodeAt(0))
}
const toB64Url = (buf: ArrayBuffer | null) =>
  buf ? btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '') : ''
const SW_URL = '/app/sw.js'

export default function NotificationSettings() {
  const qc = useQueryClient()
  const ev = useQuery({ queryKey: ['nt-events'], queryFn: () => get<Events>('/notifications/events') })
  const pr = useQuery({ queryKey: ['nt-prefs'], queryFn: () => get<Prefs>('/notifications/preferences') })
  const [prefs, setPrefs] = useState<Prefs['prefs']>({}), [email, setEmail] = useState(''), [phone, setPhone] = useState('')
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  useEffect(() => { if (pr.data) { setPrefs(pr.data.prefs); setEmail(pr.data.contact.email ?? ''); setPhone(pr.data.contact.phone ?? '') } }, [pr.data])
  const run = async (fn: () => Promise<string>) => { try { setMsg({ ok: true, text: await fn() }) } catch (x) { setMsg({ ok: false, text: (x as Error).message }) } }
  if (ev.isLoading || pr.isLoading) return <Spinner />
  if (ev.error || pr.error) return <ErrorBox error={ev.error ?? pr.error} />
  const channels = ev.data!.channels
  const avail = Object.fromEntries(channels.map(c => [c.code, c.available]))
  const toggle = (e: string, c: string, v: boolean) => setPrefs(p => ({ ...p, [e]: { ...(p[e] ?? {}), [c]: v } }))
  const pushSupported = 'serviceWorker' in navigator && 'PushManager' in window
  const enablePush = () => run(async () => {
    if (!pushSupported) throw new Error('مرورگر شما از Web Push پشتیبانی نمی‌کند')
    if ((await Notification.requestPermission()) !== 'granted') throw new Error('اجازهٔ اعلان داده نشد')
    const k = await get<{ key: string }>('/push/vapid-public-key')
    const reg = await navigator.serviceWorker.register(SW_URL)
    const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: fromB64Url(k.key) })
    await send('/push/subscribe', { endpoint: sub.endpoint, keys: { p256dh: toB64Url(sub.getKey('p256dh')), auth: toB64Url(sub.getKey('auth')) } })
    qc.invalidateQueries({ queryKey: ['nt-prefs'] })
    return 'این مرورگر برای اعلان ثبت شد'
  })
  const disablePush = () => run(async () => {
    const reg = await navigator.serviceWorker.getRegistration(SW_URL)
    const sub = await reg?.pushManager.getSubscription()
    if (sub) { await send('/push/unsubscribe', { endpoint: sub.endpoint }); await sub.unsubscribe() }
    qc.invalidateQueries({ queryKey: ['nt-prefs'] })
    return 'لغو شد'
  })
  return (
    <Card title="تنظیمات اعلان">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr><th className="th">رویداد</th>{channels.map(c => <th key={c.code} className="th">{c.label}{!c.available && <small className="text-mut"> (پیکربندی نشده)</small>}</th>)}</tr></thead>
          <tbody>{ev.data!.events.map(e => (
            <tr key={e.code}><td className="td">{e.title}</td>{channels.map(c => (
              <td key={c.code} className="td"><input type="checkbox" aria-label={`${e.title} ${c.label}`} checked={!!prefs[e.code]?.[c.code]} disabled={c.code !== 'inapp' && !avail[c.code]} onChange={x => toggle(e.code, c.code, x.target.checked)} /></td>
            ))}</tr>
          ))}</tbody>
        </table>
      </div>
      <Btn className="mt-2" onClick={() => run(async () => { await send('/notifications/preferences', { prefs }, 'PUT'); return 'تنظیمات ذخیره شد' })}>ذخیره تنظیمات</Btn>
      <h4 className="mb-1 mt-4 font-semibold">اطلاعات تماس</h4>
      <div className="grid gap-2 sm:grid-cols-2">
        <label className="flex flex-col gap-1">ایمیل<input className="inp" type="email" dir="ltr" value={email} onChange={e => setEmail(e.target.value)} /></label>
        <label className="flex flex-col gap-1">موبایل<input className="inp" dir="ltr" placeholder="+989123456789" value={phone} onChange={e => setPhone(e.target.value)} /></label>
      </div>
      <Btn className="mt-2" variant="ghost" onClick={() => run(async () => { await send('/me/contact', { email, phone }, 'PUT'); return 'اطلاعات تماس ذخیره شد' })}>ذخیره</Btn>
      <h4 className="mb-1 mt-4 font-semibold">ارسال آزمایشی</h4>
      <div className="flex flex-wrap gap-2">
        {['email', 'sms', 'webpush'].map(code => (
          <Btn key={code} variant="ghost" disabled={!avail[code]} onClick={() => run(async () => {
            const r = await send<{ status: string; error?: string }>('/notifications/test', { channel: code })
            return r.status === 'sent' ? 'ارسال شد' : `نتیجه: ${r.status}${r.error ? ` — ${r.error}` : ''}`
          })}>{channels.find(c => c.code === code)?.label ?? code}</Btn>
        ))}
      </div>
      <h4 className="mb-1 mt-4 font-semibold">اعلان مرورگر</h4>
      <p className="text-sm text-mut">{faDigits(pr.data!.push_subscriptions)} مرورگر ثبت‌شده</p>
      <div className="mt-1 flex gap-2">
        <Btn variant="ghost" disabled={!avail.webpush || !pushSupported} onClick={enablePush}>فعال‌سازی در این مرورگر</Btn>
        <Btn variant="ghost" disabled={!pushSupported} onClick={disablePush}>لغو در این مرورگر</Btn>
      </div>
      {msg && <p role={msg.ok ? 'status' : 'alert'} className={`mt-2 ${msg.ok ? 'text-ok' : 'text-bad'}`}>{msg.text}</p>}
    </Card>
  )
}

