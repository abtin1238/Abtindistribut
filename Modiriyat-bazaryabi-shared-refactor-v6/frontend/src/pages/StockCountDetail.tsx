import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { get, send } from '../lib/api'
import { fmtCell } from '../lib/fa'
import type { Row } from '../lib/types'
import { Btn, Card, ErrorBox, Spinner } from '../components/ui'

const STATUS: Record<string, string> = { draft: 'پیش‌نویس', counting: 'در حال شمارش', approved: 'تأییدشده', cancelled: 'لغوشده' }

export default function StockCountDetail() {
  const { id } = useParams(), qc = useQueryClient()
  const q = useQuery({ queryKey: ['stock-count', id], queryFn: () => get<Row>(`/stock/counts/${id}`) })
  const [vals, setVals] = useState<Record<number, string>>({}), [reason, setReason] = useState(''), [msg, setMsg] = useState(''), [err, setErr] = useState<unknown>(null)
  const c = q.data
  const editable = !!c && (c.status === 'draft' || c.status === 'counting')
  const refresh = () => { setVals({}); qc.invalidateQueries({ queryKey: ['stock-count', id] }); qc.invalidateQueries({ queryKey: ['stock-counts'] }); qc.invalidateQueries({ queryKey: ['stock'] }) }
  async function run(label: string, fn: () => Promise<unknown>) {
    setErr(null); setMsg('')
    try { await fn(); setMsg(`«${label}» انجام شد.`); refresh() } catch (e) { setErr(e) }
  }
  const dirty = Object.entries(vals).filter(([, v]) => v !== '').map(([k, v]) => ({ product_id: Number(k), counted_qty: Number(v) }))
  if (q.isLoading) return <Spinner />
  if (q.error || !c) return <ErrorBox error={q.error} />
  return (
    <section className="flex flex-col gap-3 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="me-auto text-lg font-bold">انبارگردانی {c.number}</h2>
        <span className="rounded bg-ctl px-2 py-1 text-sm ">{STATUS[c.status] ?? c.status}</span>
        <Link className="text-bl underline" to="/stock-counts">بازگشت به فهرست</Link>
      </div>
      {c.note && <p className="text-mut">{c.note}</p>}
      {msg && <p role="status" className="rounded bg-ok-soft p-2 text-ok ">{msg}</p>}
      {err != null && <ErrorBox error={err} />}
      <div className="overflow-x-auto rounded border border-bd ">
        <table className="w-full text-sm">
          <thead><tr>{['کالا', 'کد', 'موجودی سیستم', 'شمارش', 'اختلاف', 'ارزش اختلاف'].map(h => <th key={h} className="th">{h}</th>)}</tr></thead>
          <tbody>
            {(c.lines as Row[]).map(l => {
              const typed = vals[l.product_id]
              const counted = typed !== undefined && typed !== '' ? Number(typed) : l.counted_qty
              const diff = counted == null ? null : Number(counted) - Number(l.system_qty)
              return (
                <tr key={l.product_id}>
                  <td className="td">{l.product}</td><td className="td">{l.sku}</td>
                  <td className="td">{fmtCell('num', l.system_qty)}</td>
                  <td className="td">{editable
                    ? <input aria-label={`شمارش ${l.product}`} className="inp w-28" type="number" min="0" inputMode="decimal" value={typed ?? (l.counted_qty ?? '')} onChange={e => setVals(v => ({ ...v, [l.product_id]: e.target.value }))} />
                    : fmtCell('num', l.counted_qty)}</td>
                  <td className={`td ${diff ? (diff < 0 ? 'text-bad' : 'text-ok') : ''}`}>{diff == null ? '—' : fmtCell('num', diff)}</td>
                  <td className="td">{diff == null ? '—' : fmtCell('money', diff * Number(l.avg_cost))}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <Card title="جمع ارزش اختلاف (شمارش‌شده‌ها)"><p className="text-lg">{fmtCell('money', c.total_value_difference)} ریال — {fmtCell('num', c.counted_lines)} از {fmtCell('num', c.lines.length)} قلم شمارش شده</p></Card>
      {editable && (
        <div className="flex flex-wrap items-end gap-2">
          <Btn disabled={!dirty.length} onClick={() => run('ذخیره شمارش', () => send(`/stock/counts/${id}/lines`, { lines: dirty }, 'PUT'))}>ذخیره شمارش</Btn>
          <label className="flex flex-col gap-1">دلیل / توضیح تأیید
            <input className="inp" value={reason} onChange={e => setReason(e.target.value)} placeholder="مثلاً انبارگردانی پایان ماه" />
          </label>
          <Btn disabled={c.status !== 'counting' || dirty.length > 0} title={dirty.length ? 'ابتدا شمارش را ذخیره کنید' : undefined}
            onClick={() => window.confirm('اختلاف‌ها در موجودی و دفتر کل اعمال می‌شود و قابل برگشت نیست. تأیید؟') && run('تأیید انبارگردانی', () => send(`/stock/counts/${id}/approve`, { reason }))}>تأیید و اعمال اختلاف‌ها</Btn>
          <Btn variant="danger" onClick={() => window.confirm('برگه لغو شود؟') && run('لغو', () => send(`/stock/counts/${id}/cancel`))}>لغو برگه</Btn>
        </div>
      )}
    </section>
  )
}
