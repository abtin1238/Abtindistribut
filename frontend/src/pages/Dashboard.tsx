import { useQuery } from '@tanstack/react-query'
import { get } from '../lib/api'
import { faMoney, faDigits } from '../lib/fa'
import { Card, ErrorBox, Spinner } from '../components/ui'
const LABELS: Record<string, [string, boolean]> = {
  sales_today: ['فروش امروز', true], orders_today: ['سفارش‌های امروز', false], open_invoices: ['فاکتورهای باز', false], customers: ['مشتریان فعال', false],
  stock_value: ['ارزش موجودی', true], receivables: ['مطالبات', true], payables: ['بدهی‌ها', true],
}
export function Kpis({ data }: { data: Record<string, unknown> }) {
  const items = Object.entries(data).filter(([, v]) => typeof v === 'number' || (typeof v === 'string' && v !== '' && !isNaN(Number(v))))
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {items.map(([k, v]) => {
        const [label, money] = LABELS[k] ?? [k, false]
        return <Card key={k}><p className="text-sm text-slate-500">{label}</p><p className="text-xl font-bold">{money ? faMoney(Number(v)) : faDigits(Number(v))}</p></Card>
      })}
    </div>
  )
}
export function Bars({ rows }: { rows: { day: string; total: number | string }[] }) {
  const vals = rows.map(r => Number(r.total)), max = Math.max(1, ...vals), w = 100 / Math.max(1, rows.length)
  return (
    <svg role="img" aria-label="روند فروش" viewBox="0 0 100 40" preserveAspectRatio="none" className="h-40 w-full">
      {rows.map((r, i) => { const h = (Number(r.total) / max) * 36; return <rect key={r.day} x={i * w + w * 0.1} y={38 - h} width={w * 0.8} height={Math.max(0.3, h)} className="fill-blue-500"><title>{`${r.day}: ${faMoney(Number(r.total))}`}</title></rect> })}
    </svg>
  )
}
export default function Dashboard() {
  const d = useQuery({ queryKey: ['dashboard'], queryFn: () => get<Record<string, unknown>>('/dashboard') })
  const t = useQuery({ queryKey: ['dashboard-trend'], queryFn: () => get<{ day: string; total: number }[]>('/dashboard/trend?days=30') })
  return (
    <section className="flex flex-col gap-4 p-4">
      <h2 className="text-lg font-bold">داشبورد</h2>
      {d.isLoading ? <Spinner /> : d.error ? <ErrorBox error={d.error} /> : <Kpis data={d.data ?? {}} />}
      <Card title="فروش ۳۰ روز اخیر">{t.isLoading ? <Spinner /> : t.error ? <ErrorBox error={t.error} /> : <Bars rows={t.data ?? []} />}</Card>
    </section>
  )
}
