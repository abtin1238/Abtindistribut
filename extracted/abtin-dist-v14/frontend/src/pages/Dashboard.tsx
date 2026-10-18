import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { get } from '../lib/api'
import { can, useMe } from '../lib/useMe'
import { auditEnt, auditAct } from '../lib/auditLabels'
import { faDigits } from '../lib/fa'
import { Empty, ErrorBox, Spinner } from '../components/ui'
import { Donut, LineChart, type Point } from '../components/Charts'
import { KpiCard } from '../components/KpiCard'
import { DashMap } from '../components/DashMap'
import { Icon } from '../components/Icon'

type Dash = { stock_value?: number; orders_today?: number; sales_today?: number; payments_today?: number; receivables?: number; customers?: number }
type Audit = { id: number; created_at: string; user_id: number | null; action: string; entity: string; entity_id: number | null }
const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
const rep = (name: string, p: Record<string, string> = {}) => `/reports?${new URLSearchParams({ name, ...p }).toString()}`
const ET: Record<string, [string, string]> = {
  order: ['cart', 'bl'], customer: ['users', 'warn'], product: ['box', 'pur'], stock: ['box', 'pur'], payment: ['wallet', 'ok'], delivery: ['truck', 'info'],
  document: ['doc', 'bl'], journal: ['bars', 'cy'], price_rule: ['trend', 'pink'], purchase: ['cart', 'warn'], check: ['wallet', 'warn'], visit: ['users', 'ok'],
}
const clock = (v: string) => new Date(/Z|[+-]\d\d:?\d\d$/.test(v) ? v : `${v}Z`).toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' })

function Activity() {
  const q = useQuery({ queryKey: ['dash-audit'], queryFn: () => get<Audit[]>('/audit').then(r => [...r].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at))).slice(0, 5)) })
  if (q.isLoading) return <Spinner />
  if (q.error) return <ErrorBox error={q.error} />
  if (!q.data?.length) return <Empty>فعالیتی ثبت نشده است.</Empty>
  return (
    <ul id="act">{q.data.map(a => {
      const [ic, tone] = ET[a.entity] ?? ['doc', 'bl']
      return (
        <li key={a.id}>
          <span className="ai" data-tone={tone}><Icon n={ic} /></span>
          <div>{auditEnt(a.entity)} {auditAct(a.action)}{a.entity_id ? ` #${faDigits(a.entity_id)}` : ''}</div>
          <time>{clock(a.created_at)}</time>
        </li>
      )
    })}</ul>
  )
}

export default function Dashboard() {
  const me = useMe()
  const [days, setDays] = useState(30)
  const sales = can(me.data, 'sales.read')
  const d = useQuery({ queryKey: ['dashboard'], queryFn: () => get<Dash>('/dashboard') })
  const trend = useQuery({ queryKey: ['dashboard-trend', days], enabled: sales, queryFn: () => get<Point[]>(`/dashboard/trend?days=${days}`) })
  const cats = useQuery({ queryKey: ['dashboard-cat', days], enabled: sales, queryFn: () => get<{ name: string; total: number | string }[]>(`/dashboard/by-category?days=${days}`) })
  const today = iso(new Date()), v = d.data
  const ts = trend.data ?? [], td = Number(ts.at(-1)?.total ?? 0), yd = Number(ts.at(-2)?.total ?? 0)
  const pct = yd > 0 ? Math.round(((td - yd) / yd) * 100) : null
  const kpis: { show: boolean; label: string; value: number | undefined; money?: boolean; to: string; icon: string; tone: 'g' | 'b' | 'p' | 'o' | 'r' | 't' }[] = [
    { show: can(me.data, 'inventory.read'), label: 'موجودی انبار', value: v?.stock_value, money: true, to: rep('inventory', { kind: 'stock' }), icon: 'box', tone: 'p' },
    { show: sales, label: 'فاکتورهای امروز', value: v?.orders_today, to: '/orders', icon: 'doc', tone: 'b' },
    { show: sales, label: 'فروش امروز', value: v?.sales_today, money: true, to: rep('sales', { by: 'customer', start: today, end: today }), icon: 'trend', tone: 'g' },
    { show: can(me.data, 'finance.read'), label: 'دریافت امروز', value: v?.payments_today, money: true, to: '/payments', icon: 'wallet', tone: 't' },
    { show: can(me.data, 'finance.read'), label: 'بدهی مشتریان', value: v?.receivables, money: true, to: rep('aging'), icon: 'alert', tone: 'r' },
    { show: can(me.data, 'crm.read'), label: 'مشتریان فعال', value: v?.customers, to: '/customers', icon: 'users', tone: 'o' },
  ]
  const hr = new Date().getHours(), greet = hr < 12 ? 'صبح بخیر' : hr < 17 ? 'ظهر بخیر' : hr < 20 ? 'عصر بخیر' : 'شب بخیر'
  const date = new Intl.DateTimeFormat('fa-IR-u-ca-persian', { weekday: 'long', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
  const quick: [string, string, string, string, boolean][] = [
    ['/orders', 'doc', 'مدیریت فاکتورها', 'مشاهده و تأیید فاکتورها', sales],
    ['/stock', 'box', 'مدیریت موجودی', 'کنترل موجودی انبار', can(me.data, 'inventory.read')],
    ['/users', 'users', 'مدیریت کاربران', 'افزودن و ویرایش کاربران', can(me.data, 'admin.read')],
    ['/reports', 'chart', 'گزارشات جامع', 'تحلیل و گزارش‌گیری', can(me.data, 'reports.read')],
    ['/settings', 'gear', 'تنظیمات سیستم', 'تنظیمات و پیکربندی', true],
  ]
  const shown = kpis.filter(k => k.show && k.value != null)
  return (
    <>
      <h1 className="sr-only">داشبورد</h1>
      <div className="top">
        {d.isLoading ? <Spinner /> : d.error ? <ErrorBox error={d.error} /> : (
          <div className="kp">
            {shown.map(k => (
              <KpiCard key={k.label} label={k.label} value={k.value!} money={k.money} to={k.to} icon={k.icon} tone={k.tone}
                badge={k.label === 'فروش امروز' && pct != null ? <em className={pct < 0 ? 'dn' : ''}>{`${pct >= 0 ? '+' : ''}${faDigits(pct)}٪`}</em> : undefined} />
            ))}
          </div>
        )}
        <section className="cd hero">
          <div className="hero-t"><h2>{greet}{me.data ? `، ${me.data.user.name}` : ''}</h2><p>امروز یک روز عالی برای رشد و پیشرفت است...</p></div>
          <HeroArt />
          <div className="date"><Icon n="cal" /><b>{date}</b><small>{me.data?.company.name}</small></div>
        </section>
      </div>

      {sales && (
        <div className="row2">
          <section className="cd">
            <header><h3>فروش بر اساس دسته‌بندی</h3></header>
            {cats.isLoading ? <Spinner /> : cats.error ? <ErrorBox error={cats.error} /> : <Donut items={(cats.data ?? []).map(x => ({ name: x.name, value: Number(x.total) }))} />}
          </section>
          <section className="cd tr">
            <header>
              <h3>روند فروش</h3>
              <select aria-label="بازه" value={days} onChange={e => setDays(Number(e.target.value))}>
                <option value={7}>۷ روز اخیر</option><option value={30}>ماه جاری</option><option value={90}>۹۰ روز</option>
              </select>
            </header>
            {trend.isLoading ? <Spinner /> : trend.error ? <ErrorBox error={trend.error} /> : <LineChart series={ts} />}
          </section>
        </div>
      )}

      <div className="row3">
        {can(me.data, 'admin.read') && (
          <section className="cd">
            <header><h3>آخرین فعالیت‌ها</h3><Link to="/audit" className="ds-link">مشاهده همه</Link></header>
            <Activity />
          </section>
        )}
        {can(me.data, 'gps.read') && <DashMap />}
      </div>

      <div className="qa">
        {quick.filter(x => x[4]).map(([to, ic, t, s]) => (
          <Link key={to} to={to}><div className="ik b"><Icon n={ic} /></div><b>{t}</b><small>{s}</small></Link>
        ))}
      </div>
    </>
  )
}

function HeroArt() {
  return (
    <svg className="hsvg" viewBox="0 0 400 220" aria-hidden="true">
      <defs><linearGradient id="mg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="var(--hero1)" /><stop offset="1" stopColor="var(--hero2)" /></linearGradient></defs>
      <path d="M0 220V150l70-60 60 40 80-80 90 90 100-50v130z" fill="url(#mg)" opacity=".6" />
      <path d="M30 195c80 25 120-35 200-12s90-55 140-90" fill="none" stroke="var(--bl)" strokeWidth="4" strokeLinecap="round" />
      <g transform="translate(150 98)"><rect width="70" height="42" rx="6" fill="var(--pur)" /><rect x="70" y="14" width="28" height="28" rx="5" fill="var(--pur)" /><circle cx="18" cy="44" r="8" fill="var(--bg0)" stroke="var(--bl2)" strokeWidth="3" /><circle cx="82" cy="44" r="8" fill="var(--bg0)" stroke="var(--bl2)" strokeWidth="3" /></g>
      <path d="M330 60a14 14 0 1 1 28 0c0 14-14 30-14 30s-14-16-14-30z" fill="var(--pur)" /><circle cx="344" cy="60" r="5" fill="#fff" />
    </svg>
  )
}
