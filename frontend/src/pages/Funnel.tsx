import { useMutation, useQuery } from '@tanstack/react-query'
import { get, send } from '../lib/api'
import { faDigits } from '../lib/fa'
import { Btn, Card, ErrorBox, Spinner } from '../components/ui'

type Stage = { count: number; value: number }
type FunnelRes = {
  leads: { total: number; stages: Record<string, Stage>; won: number; lost: number; win_rate: number | null; created_to_won: number | null; avg_days_to_win: number | null; won_value: number; lost_reasons: Record<string, number> }
  visits: { with_result: number; ordered: number; order_rate: number | null; out_of_range: number; no_order_reasons: Record<string, number> }
}
const STAGE: Record<string, string> = { new: 'جدید', contacted: 'تماس‌گرفته', qualified: 'واجد شرایط', proposal: 'پیشنهاد', negotiation: 'مذاکره', won: 'موفق', lost: 'ازدست‌رفته' }
const pct = (v: number | null) => (v == null ? '—' : `${faDigits((v * 100).toLocaleString('en-US', { maximumFractionDigits: 1 }))}٪`)
const n = (v: number | null | undefined) => (v == null ? '—' : faDigits(Number(v).toLocaleString('en-US')))
const Stat = ({ label, value, sub }: { label: string; value: string; sub?: string }) => (
  <div className="rounded-lg border border-bd p-3 "><div className="text-sm text-mut">{label}</div><b className="text-lg">{value}</b>{sub && <div className="text-xs text-mut">{sub}</div>}</div>
)
const Rows = ({ head, rows }: { head: string[]; rows: string[][] }) => (
  <table className="w-full text-sm"><thead><tr>{head.map(h => <th key={h} className="th">{h}</th>)}</tr></thead>
    <tbody>{rows.length ? rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j} className="td">{c}</td>)}</tr>) : <tr><td className="td" colSpan={head.length}>—</td></tr>}</tbody></table>
)

export default function Funnel() {
  const q = useQuery({ queryKey: ['funnel'], queryFn: () => get<FunnelRes>('/automation/funnel') })
  const remind = useMutation({ mutationFn: () => send<{ notified: number }>('/automation/run-reminders') })
  if (q.isLoading) return <Spinner />
  if (q.error) return <ErrorBox error={q.error} />
  const { leads: L, visits: V } = q.data!
  return (
    <section className="mx-auto flex max-w-4xl flex-col gap-4 p-4">
      <div className="flex items-center gap-2">
        <h2 className="me-auto text-lg font-bold">تفکیک مشتریان</h2>
        <Btn variant="ghost" disabled={remind.isPending} onClick={() => remind.mutate()}>اجرای یادآوری‌ها</Btn>
      </div>
      {remind.data && <p role="status" className="text-ok">{n(remind.data.notified)} اعلان ارسال شد</p>}
      {remind.error != null && <ErrorBox error={remind.error} />}
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Stat label="مشتریان بالقوه" value={n(L.total)} />
        <Stat label="نرخ برد" value={pct(L.win_rate)} sub={`از ${n(L.won + L.lost)} بسته‌شده`} />
        <Stat label="ایجاد تا برد" value={pct(L.created_to_won)} />
        <Stat label="میانگین روز تا برد" value={n(L.avg_days_to_win)} />
        <Stat label="ارزش بردها" value={n(L.won_value)} />
        <Stat label="ویزیت→سفارش" value={pct(V.order_rate)} sub={`${n(V.ordered)} از ${n(V.with_result)}`} />
        <Stat label="ویزیت خارج از شعاع" value={n(V.out_of_range)} />
      </div>
      <Card title="مراحل تفکیک مشتریان"><Rows head={['مرحله', 'تعداد', 'ارزش']} rows={Object.entries(L.stages).map(([k, v]) => [STAGE[k] ?? k, n(v.count), n(v.value)])} /></Card>
      <Card title="دلایل ازدست‌رفتن مشتریان بالقوه"><Rows head={['دلیل', 'تعداد']} rows={Object.entries(L.lost_reasons).map(([k, v]) => [k, n(v)])} /></Card>
      <Card title="دلایل عدم سفارش در ویزیت"><Rows head={['دلیل', 'تعداد']} rows={Object.entries(V.no_order_reasons).map(([k, v]) => [k, n(v)])} /></Card>
    </section>
  )
}
