import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { get, send } from '../lib/api'
import { Btn, ErrorBox } from './ui'
import { FormDialog } from './FormDialog'

type Session = { created_at?: string; ip?: string; user_agent?: string; current?: boolean }
type User = { name: string; username: string; role: string }

export default function AccountDialog({ user, onClose, onLogout }: { user?: User; onClose: () => void; onLogout: () => void }) {
  const qc = useQueryClient()
  const [pw, setPw] = useState(false), [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const sessions = useQuery({ queryKey: ['sessions'], queryFn: () => get<Session[]>('/auth/sessions') })
  async function closeOthers() {
    try { const r = await send<{ revoked: number }>('/auth/logout-all'); setMsg({ ok: true, text: `${r.revoked} نشست بسته شد` }); qc.invalidateQueries({ queryKey: ['sessions'] }) }
    catch (x) { setMsg({ ok: false, text: (x as Error).message }) }
  }
  if (pw) return (
    <FormDialog title="تغییر رمز عبور" onClose={() => { setPw(false); onClose() }}
      fields={[{ name: 'old_password', label: 'رمز فعلی', type: 'password', required: true }, { name: 'new_password', label: 'رمز جدید (حداقل ۸ نویسه؛ در production ۱۲)', type: 'password', required: true }, { name: 'repeat', label: 'تکرار رمز جدید', type: 'password', required: true }]}
      onSubmit={async v => {
        if (v.new_password !== v.repeat) throw new Error('تکرار رمز با رمز جدید یکسان نیست')
        await send('/auth/change-password', { old_password: v.old_password, new_password: v.new_password })
      }} />
  )
  return (
    <div role="dialog" aria-modal="true" aria-label="حساب کاربری" className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center">
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-t-xl bg-card p-4 sm:rounded-xl">
        <h3 className="text-lg font-bold">حساب کاربری</h3>
        <p className="text-sm text-mut">{user?.name} — {user?.username} ({user?.role})</p>
        <div className="my-3 flex flex-wrap gap-2">
          <Btn variant="ghost" onClick={() => setPw(true)}>تغییر رمز عبور</Btn>
          <Btn variant="ghost" onClick={closeOthers}>بستن نشست‌های دیگر</Btn>
          <Btn onClick={onLogout}>خروج</Btn>
        </div>
        {msg && <p role={msg.ok ? 'status' : 'alert'} className={msg.ok ? 'text-ok' : 'text-bad'}>{msg.text}</p>}
        <h4 className="mb-1 font-semibold">نشست‌های فعال</h4>
        {sessions.isLoading ? <p>…</p> : sessions.error ? <ErrorBox error={sessions.error} /> : (
          <div className="overflow-x-auto"><table className="w-full text-sm">
            <thead><tr><th className="th">شروع</th><th className="th">IP</th><th className="th">دستگاه</th><th className="th" /></tr></thead>
            <tbody>{sessions.data?.map((s, i) => (
              <tr key={i}><td className="td">{s.created_at ? s.created_at.replace('T', ' ').slice(0, 16) : '—'}</td><td className="td" dir="ltr">{s.ip || '—'}</td>
                <td className="td">{(s.user_agent || '—').slice(0, 40)}</td><td className="td">{s.current && <b>این نشست</b>}</td></tr>
            ))}</tbody></table></div>
        )}
        <div className="mt-3"><Btn variant="ghost" onClick={onClose}>بستن</Btn></div>
      </div>
    </div>
  )
}
