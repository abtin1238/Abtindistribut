import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { get } from '../lib/api'
import { drillTarget, type Drill } from '../lib/drill'
import { faCompact, faDigits, faMoney, faPct } from '../lib/fa'
import { Card, Empty, ErrorBox, Spinner } from '../components/ui'
import { LineChart, type Point } from '../components/Charts'
import { KpiCard } from '../components/KpiCard'
import { GeneralLedgerDialog } from '../components/LedgerDialog'

type N = number | string
type Kpi = { value: N; drill?: Drill } & Record<string, unknown>
type Bucket = { amount: N; count: N }
type Summary = {
  kpis: Record<string, Kpi | undefined>; month_start: string; date: string
  tops?: { product?: { name: string; net: N; share: N }[]; customer?: { name: string; net: N; share: N }[] }
  staff?: {
    targets?: { user_name: string; actual: N; sales_target: N; attainment_percent: N | null; commission: N }[]
    visitors?: { name: string; visits: N; conversion: N; out_of_range: N }[]
    drivers?: { name: string; delivered: N; failed: N; success_rate: N; avg_minutes: N | null }[]
  }
}
type Holding = { companies: { name: string; current?: boolean; kpis: Record<string, { value: N } | undefined> }[]; consolidated: Record<string, N>; warnings: string[] }
type Recon = { all_ok: boolean; checks: { name: string; note?: string; a: N; b: N; diff: N; ok: boolean }[] }
type Liquidity = { cash_now: N; forecast: { days: N; inflow: N; outflow: N; projected: N }[]; note: string }
type Checks = { received: Record<string, Bucket>; paid: Record<string, Bucket> }

const M = (v: N | null | undefined) => (v == null || v === '' ? '—' : faMoney(Number(v)))
const num = (v: N) => faDigits(Number(v).toLocaleString('en-US'))
const BUCKETS: [string, string][] = [['overdue', 'سررسیدگذشته'], ['d7', 'تا ۷ روز'], ['d30', '۸ تا ۳۰ روز'], ['later', 'بعد از ۳۰ روز']]
const HOLD: [string, string][] = [['sales_month', 'فروش ماه'], ['gross_profit_month', 'سود ناخالص ماه'], ['receivables', 'بدهی مشتریان'], ['payables', 'بدهی به تأمین‌کنندگان'], ['cash', 'نقد و بانک'], ['stock_value', 'ارزش موجودی']]

function Table({ head, rows }: { head: string[]; rows: React.ReactNode[][] }) {
  return (
    <div className="overflow-x-auto"><table className="w-full text-sm">
      <thead><tr>{head.map(h => <th key={h} className="th">{h}</th>)}</tr></thead>
      <tbody>{rows.length ? rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j} className="td">{c}</td>)}</tr>) : <tr><td className="td" colSpan={head.length}>داده‌ای نیست</td></tr>}</tbody>
    </table></div>
  )
}
const Denied = () => <Empty>دسترسی مالی ندارید</Empty>

export default function Ceo() {
  const nav = useNavigate()
  const [days, setDays] = useState(30), [ledger, setLedger] = useState<string | null>(null)
  const sm = useQuery({ queryKey: ['ceo'], queryFn: () => get<Summary>('/ceo/summary') })
  const tr = useQuery({ queryKey: ['ceo-trend', days], queryFn: () => get<{ series: Point[] }>(`/ceo/trend?days=${days}`) })
  const ho = useQuery({ queryKey: ['ceo-holding'], queryFn: () => get<Holding>('/ceo/holding') })
  const rc = useQuery({ queryKey: ['ceo-recon'], queryFn: () => get<Recon>('/ceo/reconcile') })
  if (sm.isLoading) return <Spinner />
  if (sm.error) return <ErrorBox error={sm.error} />
  const k = sm.data!.kpis, T = sm.data!.tops ?? {}, S = sm.data!.staff ?? {}
  const go = (key: string) => () => { const t = drillTarget(k[key]?.drill); if (!t) return; if (t.kind === 'ledger') setLedger(t.code); else nav(t.to) }
  const money = (key: string, label: string, sub?: string) => (k[key] ? <KpiCard key={key} label={label} value={k[key]!.value as N} money onClick={go(key)} sub={sub} /> : null)
  const count = (key: string, label: string) => (k[key] ? <KpiCard key={key} label={label} value={k[key]!.value as N} onClick={go(key)} /> : null)
  const gp = k.gross_profit_month, cash = k.cash, sv = k.stock_value
  const liq = k.liquidity as unknown as Liquidity | undefined, chk = k.checks as unknown as Checks | undefined
  const range = { start: sm.data!.month_start, end: sm.data!.date }
  return (
    <section className="mx-auto flex max-w-6xl flex-col gap-4 p-4">
      <div className="flex items-center gap-2">
        <div className="me-auto"><h2 className="text-lg font-bold">داشبورد مدیرعامل</h2><p className="text-sm text-mut">همهٔ اعداد از دفتر کل و پایگاه داده؛ با کلیک روی هر کارت به گزارش و سند مربوط بروید.</p></div>
        <Link to="/reports" className="rounded border border-bd px-3 py-1 text-sm">گزارش‌ها</Link>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {money('sales_today', 'فروش امروز')}{money('sales_month', 'فروش ماه')}
        {money('gross_profit_month', 'سود ناخالص ماه', gp ? `حاشیه ${faPct(gp.margin_percent as N)}${Number(gp.uncosted_lines) ? ` — ${num(gp.uncosted_lines as N)} سطر بدون بها` : ''}` : undefined)}
        {money('receivables', 'بدهی مشتریان')}
        {money('cash', 'نقد و بانک', cash ? `صندوق ${M(cash.cash as N)} — بانک ${M(cash.bank as N)}` : undefined)}
        {money('payables', 'بدهی به تأمین‌کنندگان')}
        {money('stock_value', 'ارزش موجودی (بر پایهٔ بها)', sv && Number(sv.unvalued_products) ? `${num(sv.unvalued_products as N)} کالا بدون بها` : undefined)}
        {count('low_stock', 'کالای کم‌موجودی')}{money('payments_today', 'دریافت امروز')}{count('orders_today', 'سفارش امروز')}{count('customers', 'مشتریان فعال')}{count('active_deliveries', 'مأموریت در جریان')}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="روند فروش">
          <select aria-label="بازهٔ روند" className="inp mb-2 w-auto" value={days} onChange={e => setDays(Number(e.target.value))}>{[7, 30, 90].map(n => <option key={n} value={n}>{faDigits(n)} روز اخیر</option>)}</select>
          {tr.isLoading ? <Spinner /> : tr.error ? <ErrorBox error={tr.error} /> : <LineChart series={tr.data?.series ?? []} />}
        </Card>
        <Card title="نقدینگی و پیش‌بینی">
          {liq ? (<>
            <p className="mb-2 text-lg font-bold">{faCompact(liq.cash_now).n} <small className="font-normal text-mut">{faCompact(liq.cash_now).unit} تومان نقد و بانک</small></p>
            <Table head={['افق', 'چک دریافتی', 'چک پرداختی', 'پیش‌بینی نقد']} rows={liq.forecast.map(f => [`${num(f.days)} روز`, M(f.inflow), M(f.outflow), M(f.projected)])} />
            <p className="mt-2 text-sm text-mut">{liq.note}</p>
          </>) : <Denied />}
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="چک‌ها بر اساس سررسید">
          {chk ? <Table head={['سررسید', 'دریافتی (تعداد)', 'دریافتی (مبلغ)', 'پرداختی (تعداد)', 'پرداختی (مبلغ)']}
            rows={BUCKETS.map(([b, l]) => [l, num(chk.received[b]?.count ?? 0), M(chk.received[b]?.amount), num(chk.paid[b]?.count ?? 0), M(chk.paid[b]?.amount)])} /> : <Denied />}
          <Link to="/checks" className="mt-2 block text-sm text-bl">خزانه و چک</Link>
        </Card>
        <Card title="برترین کالاها و مشتریان (ماه جاری)">
          <Table head={['کالا', 'فروش خالص', 'سهم']} rows={(T.product ?? []).map(r => [r.name, M(r.net), faPct(r.share)])} />
          <h4 className="mb-1 mt-3 font-semibold">برترین مشتریان</h4>
          <Table head={['مشتری', 'فروش خالص', 'سهم']} rows={(T.customer ?? []).map(r => [r.name, M(r.net), faPct(r.share)])} />
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="عملکرد کارکنان">
          <Table head={['فروشنده', 'فروش ماه', 'هدف', 'تحقق', 'پورسانت']} rows={(S.targets ?? []).map(r => [r.user_name, M(r.actual), Number(r.sales_target) ? M(r.sales_target) : '—',
            r.attainment_percent == null ? '—' : <span key="p" className="flex items-center gap-2"><progress max={Math.max(Number(r.sales_target), 1)} value={Math.min(Number(r.actual), Math.max(Number(r.sales_target), 1))} />{faPct(r.attainment_percent)}</span>, M(r.commission)])} />
          {S.visitors && <div className="mt-3"><Table head={['بازاریاب', 'ویزیت', 'تبدیل', 'خارج از شعاع']} rows={S.visitors.map(r => [r.name, num(r.visits), faPct(r.conversion), num(r.out_of_range)])} /></div>}
          <Link to={`/reports?${new URLSearchParams({ name: 'visitors', ...range })}`} className="mt-2 block text-sm text-bl">جزئیات بازاریاب‌ها</Link>
        </Card>
        <Card title="مأمورین پخش">
          <Table head={['مأمور', 'تحویل', 'ناموفق', 'موفقیت', 'میانگین (دقیقه)']} rows={(S.drivers ?? []).map(r => [r.name, num(r.delivered), num(r.failed), faPct(r.success_rate), r.avg_minutes == null ? '—' : num(Math.round(Number(r.avg_minutes)))])} />
          <Link to={`/reports?${new URLSearchParams({ name: 'drivers', ...range })}`} className="mt-2 block text-sm text-bl">جزئیات مأمورین</Link>
        </Card>
      </div>
      <Card title="مقایسهٔ شرکت‌های هلدینگ و تجمیع">
        {ho.isLoading ? <Spinner /> : ho.error ? <Empty>{(ho.error as Error).message}</Empty> : ho.data && (<>
          <Table head={['شرکت', ...HOLD.map(h => h[1])]} rows={[
            ...ho.data.companies.map(c => [<>{c.name}{c.current && <small className="ms-1 text-mut">(جاری)</small>}</>, ...HOLD.map(([key]) => M(c.kpis[key]?.value))]),
            ['جمع تجمیعی', ...HOLD.map(([key]) => (ho.data!.consolidated[key] !== undefined ? M(ho.data!.consolidated[key]) : '—'))]]} />
          {ho.data.warnings.map(w => <p key={w} className="mt-1 text-sm text-mut">{w}</p>)}
        </>)}
      </Card>
      <Card title="تطبیق عددها با دفتر کل">
        {rc.isLoading ? <Spinner /> : rc.error ? <Empty>{(rc.error as Error).message}</Empty> : rc.data && (<>
          <p className={`mb-2 font-semibold ${rc.data.all_ok ? 'text-ok' : 'text-bad'}`}>{rc.data.all_ok ? 'همه منطبق' : 'اختلاف دارد'}</p>
          <Table head={['بررسی', 'مقدار اول', 'مقدار دوم', 'اختلاف', 'وضعیت']} rows={rc.data.checks.map(c => [<>{c.name}{c.note && <small className="block text-bad">{c.note}</small>}</>, M(c.a), M(c.b), M(c.diff), c.ok ? 'منطبق' : 'اختلاف'])} />
        </>)}
      </Card>
      {ledger && <GeneralLedgerDialog code={ledger} onClose={() => setLedger(null)} />}
    </section>
  )
}
