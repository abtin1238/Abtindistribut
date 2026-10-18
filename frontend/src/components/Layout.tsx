import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { get, send, setToken } from '../lib/api'
import { can, useMe } from '../lib/useMe'
import { navGroups } from '../nav'
import { faDigits } from '../lib/fa'
import { applyTheme, currentTheme } from '../lib/theme'
import { applyDefaultMode, applyTokens, type ThemeCfg } from '../lib/tokens'
import { Icon, Logo } from './Icon'
import AccountDialog from './AccountDialog'

type Brand = { name?: string; tagline?: string; logo_url?: string | null }
const GROUP_ICON: Record<string, string> = { 'اصلی': 'home', 'فروش': 'cart', 'کالا و انبار': 'box', 'مالی': 'wallet', 'منابع انسانی': 'users', 'مدیریت': 'gear' }
const DEFAULT_OPEN = ['اصلی', 'فروش']

export default function Layout({ onLogout }: { onLogout: () => void }) {
  const me = useMe(), qc = useQueryClient(), nav = useNavigate(), loc = useLocation()
  const [open, setOpen] = useState(false), [acct, setAcct] = useState(false), [term, setTerm] = useState('')
  const [groups, setGroups] = useState<string[]>(DEFAULT_OPEN)
  const unread = useQuery({ queryKey: ['unread'], queryFn: () => get<{ unread: number }>('/notifications/unread-count'), refetchInterval: 60_000 })
  const brand = useQuery({ queryKey: ['brand'], queryFn: () => get<Brand>('/settings/brand'), staleTime: 600_000, retry: false })
  const themeQ = useQuery({ queryKey: ['theme'], queryFn: () => get<ThemeCfg>('/settings/theme'), staleTime: 600_000, retry: false })
  useEffect(() => { if (themeQ.data) { applyTokens(themeQ.data); applyDefaultMode(themeQ.data.mode) } }, [themeQ.data])
  const health = useQuery({
    queryKey: ['health'], staleTime: 600_000, retry: false,
    queryFn: () => fetch('/health').then(r => r.json() as Promise<{ version?: string }>).catch(() => ({} as { version?: string })),
  })
  const seg = loc.pathname.split('/')[1] ?? ''
  const activeGroup = navGroups.find(g => g.items.some(i => i.to === seg))?.title

  useEffect(() => { setOpen(false); if (activeGroup) setGroups(s => (s.includes(activeGroup) ? s : [...s, activeGroup])) }, [loc.pathname, activeGroup])
  useEffect(() => {
    document.body.classList.toggle('nav-lock', open)
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    const rs = () => { if (window.innerWidth > 1000) setOpen(false) }
    addEventListener('keydown', esc); addEventListener('resize', rs)
    return () => { removeEventListener('keydown', esc); removeEventListener('resize', rs); document.body.classList.remove('nav-lock') }
  }, [open])

  async function switchCompany(id: number) {
    const r = await send<{ token: string }>(`/auth/switch-company?company_id=${id}`)
    setToken(r.token); qc.clear(); location.reload()
  }
  async function logout() { try { await send('/auth/logout') } catch { /* نشست از قبل باطل شده */ } setToken(null); onLogout() }
  const toggleGroup = (t: string) => setGroups(s => (s.includes(t) ? s.filter(x => x !== t) : [...s, t]))
  const name = me.data?.user.name ?? 'حساب'
  const b = brand.data
  const ver = health.data?.version

  return (
    <div className={`ads${open ? ' nav-open' : ''}`}>
      <header className="hd">
        <button type="button" className="burger" aria-label="منو" aria-expanded={open} onClick={() => setOpen(o => !o)}><Icon n="menu" /></button>
        <div className="brand">
          {b?.logo_url ? <img className="logo" src={b.logo_url} alt="" /> : <Logo />}
          <div><b>{b?.name || 'Abtin Distribution'}</b><small>{b?.tagline || 'مدیریت هوشمند پخش و توزیع'}</small></div>
        </div>
        <form className="srch" role="search" onSubmit={e => { e.preventDefault(); const t = term.trim(); if (t) nav(`/search?q=${encodeURIComponent(t)}`) }}>
          <Icon n="search" />
          <input type="search" aria-label="جستجوی سراسری" placeholder="جستجو در بخش‌های مختلف سیستم..." value={term} onChange={e => setTerm(e.target.value)} />
        </form>
        <div className="hd-r">
          {(me.data?.companies.length ?? 0) > 1 && (
            <select aria-label="شرکت" className="sel" value={me.data?.company.id} onChange={e => switchCompany(Number(e.target.value))}>
              {me.data?.companies.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          )}
          <button type="button" className="tgl" aria-label="تم" onClick={() => applyTheme(currentTheme() === 'dark' ? 'light' : 'dark')}><Icon n="moon" /></button>
          <button type="button" className="bell" aria-label="اعلان‌های خوانده‌نشده" onClick={() => nav('/notifications')}>
            <Icon n="bell" />
            {(unread.data?.unread ?? 0) > 0 && <i>{faDigits(unread.data!.unread)}</i>}
          </button>
          <div className="prof" role="button" tabIndex={0} aria-label="حساب کاربری" onClick={() => setAcct(true)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') setAcct(true) }}>
            <span className="av">{name.trim()[0] ?? '?'}</span>
            <div><b>{name}</b><small>{me.data?.user.role ?? ''}</small></div>
          </div>
        </div>
      </header>

      <aside className="sb">
        <nav aria-label="منوی اصلی">
          {navGroups.map(g => {
            const items = g.items.filter(i => can(me.data, i.perm))
            if (!items.length) return null
            const isOpen = groups.includes(g.title)
            return (
              <div key={g.title} className="ds-stack">
                <button type="button" className={`nv grp${isOpen ? ' open' : ''}${!isOpen && activeGroup === g.title ? ' on' : ''}`} aria-expanded={isOpen} onClick={() => toggleGroup(g.title)}>
                  <Icon n={GROUP_ICON[g.title] ?? 'doc'} /><span>{g.title}</span><Icon n="chev" className="chev" />
                </button>
                {isOpen && items.map(i => (
                  <NavLink key={i.to} to={`/${i.to}`} className={({ isActive }) => `nv mn${isActive ? ' on' : ''}`}>{i.label}</NavLink>
                ))}
              </div>
            )
          })}
        </nav>
        <div className="onl"><i /><div><b>سیستم آنلاین</b><small>{ver ? `نسخه ${faDigits(ver)}` : ''}</small></div></div>
      </aside>
      <div className="nav-bk" onClick={() => setOpen(false)} />
      <main id="content"><Outlet /></main>
      {acct && <AccountDialog user={me.data?.user} onClose={() => setAcct(false)} onLogout={logout} />}
    </div>
  )
}
