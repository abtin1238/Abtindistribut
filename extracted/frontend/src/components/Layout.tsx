import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { get, send, setToken } from '../lib/api'
import { can, useMe } from '../lib/useMe'
import { navGroups } from '../nav'
import { faDigits } from '../lib/fa'
import { Btn } from './ui'
import { FormDialog } from './FormDialog'
const applyTheme = (dark: boolean) => { document.documentElement.classList.toggle('dark', dark); localStorage.setItem('theme', dark ? 'dark' : 'light') }
export default function Layout({ onLogout }: { onLogout: () => void }) {
  const me = useMe(), qc = useQueryClient()
  const [open, setOpen] = useState(false), [pw, setPw] = useState(false)
  const unread = useQuery({ queryKey: ['unread'], queryFn: () => get<{ unread: number }>('/notifications/unread-count'), refetchInterval: 60_000 })
  async function switchCompany(id: number) {
    const r = await send<{ token: string }>(`/auth/switch-company?company_id=${id}`)
    setToken(r.token); qc.clear(); location.reload()
  }
  async function logout() { try { await send('/auth/logout') } catch { /* نشست از قبل باطل شده */ } setToken(null); onLogout() }
  return (
    <div className="min-h-screen bg-white text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <header className="sticky top-0 z-40 flex items-center gap-2 border-b border-slate-200 bg-white p-2 dark:border-slate-700 dark:bg-slate-900">
        <Btn variant="ghost" aria-label="منو" onClick={() => setOpen(o => !o)}>☰</Btn>
        <strong className="me-auto">{me.data?.company.name ?? 'Abtin Distribution'}</strong>
        {(me.data?.companies.length ?? 0) > 1 && (
          <select aria-label="شرکت" className="inp w-auto" value={me.data?.company.id} onChange={e => switchCompany(Number(e.target.value))}>
            {me.data?.companies.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        )}
        <span aria-label="اعلان‌های خوانده‌نشده" className="px-2">🔔 {faDigits(unread.data?.unread ?? 0)}</span>
        <Btn variant="ghost" aria-label="تم" onClick={() => applyTheme(!document.documentElement.classList.contains('dark'))}>◐</Btn>
        <Btn variant="ghost" onClick={() => setPw(true)}>{me.data?.user.name ?? 'حساب'}</Btn>
        <Btn variant="ghost" onClick={logout}>خروج</Btn>
      </header>
      <div className="flex">
        <nav aria-label="منوی اصلی" className={`${open ? 'block' : 'hidden'} w-56 shrink-0 border-e border-slate-200 p-2 dark:border-slate-700 md:block`}>
          {navGroups.map(g => {
            const items = g.items.filter(i => can(me.data, i.perm))
            return items.length ? (
              <div key={g.title} className="mb-3">
                <p className="px-2 text-xs text-slate-500">{g.title}</p>
                {items.map(i => <NavLink key={i.to} to={`/${i.to}`} onClick={() => setOpen(false)} className={({ isActive }) => `block rounded px-2 py-1 ${isActive ? 'bg-blue-600 text-white' : ''}`}>{i.label}</NavLink>)}
              </div>
            ) : null
          })}
        </nav>
        <main className="min-w-0 flex-1"><Outlet /></main>
      </div>
      {pw && <FormDialog title="تغییر رمز عبور" fields={[{ name: 'old_password', label: 'رمز فعلی', type: 'password', required: true }, { name: 'new_password', label: 'رمز جدید', type: 'password', required: true }]}
        onClose={() => setPw(false)} onSubmit={v => send('/auth/change-password', v)} />}
    </div>
  )
}
