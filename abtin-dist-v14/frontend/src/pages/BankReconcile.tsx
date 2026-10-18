import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { get, send } from '../lib/api'
import { fmtCell } from '../lib/fa'
import type { Row } from '../lib/types'
import { Btn, Card, ErrorBox, Spinner } from '../components/ui'

export default function BankReconcile() {
  const qc = useQueryClient()
  const banks = useQuery({ queryKey: ['bank-accounts'], queryFn: () => get<Row[]>('/bank-accounts') })
  const [bid, setBid] = useState(''), [sel, setSel] = useState<Set<number>>(new Set()), [stmt, setStmt] = useState(''), [note, setNote] = useState('')
  const [msg, setMsg] = useState(''), [err, setErr] = useState<unknown>(null)
  const open = useQuery({ queryKey: ['reconcile', bid], enabled: !!bid, queryFn: () => get<Row>(`/bank-accounts/${bid}/reconcile`) })
  const hist = useQuery({ queryKey: ['reconciliations', bid], enabled: !!bid, queryFn: () => get<Row[]>(`/bank-accounts/${bid}/reconciliations`) })
  const lines: Row[] = open.data?.lines ?? []
  const picked = lines.filter(l => sel.has(l.line_id))
  const cleared = Number(open.data?.cleared_balance ?? 0) + picked.reduce((a, l) => a + Number(l.debit) - Number(l.credit), 0)
  const diff = stmt === '' ? null : Number(stmt) - cleared
  const refresh = () => { setSel(new Set()); setStmt(''); setNote(''); qc.invalidateQueries({ queryKey: ['reconcile', bid] }); qc.invalidateQueries({ queryKey: ['reconciliations', bid] }) }
  async function run(label: string, fn: () => Promise<unknown>) { setErr(null); setMsg(''); try { await fn(); setMsg(`«${label}» انجام شد.`); refresh() } catch (e) { setErr(e) } }
  const toggle = (id: number) => setSel(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })
  const lastId = Math.max(0, ...(hist.data ?? []).map(h => Number(h.id)))
  return (
    <section className="flex flex-col gap-3 p-4">
      <h2 className="text-lg font-bold">مغایرت‌گیری بانکی</h2>
      {banks.isLoading ? <Spinner /> : banks.error ? <ErrorBox error={banks.error} /> : (
        <select aria-label="حساب بانکی" className="inp sm:w-80" value={bid} onChange={e => { setBid(e.target.value); setSel(new Set()) }}>
          <option value="">— حساب بانکی —</option>{banks.data?.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
        </select>
      )}
      {msg && <p role="status" className="rounded bg-ok-soft p-2 text-ok ">{msg}</p>}
      {err != null && <ErrorBox error={err} />}
      {bid && open.isLoading && <Spinner />}
      {open.error != null && <ErrorBox error={open.error} />}
      {open.data && (
        <>
          <div className="grid gap-2 sm:grid-cols-4">
            <Card title="مانده دفتر"><b>{fmtCell('money', open.data.book_balance)}</b></Card>
            <Card title="مانده تطبیق‌شده‌ها"><b>{fmtCell('money', cleared)}</b></Card>
            <Card title="واریز در راه"><b>{fmtCell('money', open.data.in_transit_deposits)}</b></Card>
            <Card title="پرداخت‌های معوق"><b>{fmtCell('money', open.data.outstanding_payments)}</b></Card>
          </div>
          <div className="overflow-x-auto rounded border border-bd ">
            <table className="w-full text-sm">
              <thead><tr><th className="th">تطبیق</th>{['شماره سند', 'تاریخ', 'شرح', 'بدهکار', 'بستانکار'].map(h => <th key={h} className="th">{h}</th>)}</tr></thead>
              <tbody>
                {lines.map(l => (
                  <tr key={l.line_id}>
                    <td className="td"><input type="checkbox" aria-label={`تطبیق ${l.number}`} checked={sel.has(l.line_id)} onChange={() => toggle(l.line_id)} /></td>
                    <td className="td">{l.number}</td><td className="td">{fmtCell('date', l.date)}</td><td className="td">{l.description}</td>
                    <td className="td">{fmtCell('money', l.debit)}</td><td className="td">{fmtCell('money', l.credit)}</td>
                  </tr>
                ))}
                {!lines.length && <tr><td className="td" colSpan={6}>سطر تطبیق‌نشده‌ای نیست.</td></tr>}
              </tbody>
            </table>
          </div>
          <div className="flex flex-wrap items-end gap-2">
            <label className="flex flex-col gap-1">مانده‌ی صورت‌حساب بانک
              <input className="inp" type="number" inputMode="decimal" value={stmt} onChange={e => setStmt(e.target.value)} /></label>
            <label className="flex flex-col gap-1">توضیح
              <input className="inp" value={note} onChange={e => setNote(e.target.value)} /></label>
            <Btn disabled={!sel.size || stmt === ''} onClick={() => run('ثبت مغایرت‌گیری', () => send(`/bank-accounts/${bid}/reconcile`, { statement_balance: Number(stmt), line_ids: [...sel], note }))}>ثبت مغایرت‌گیری</Btn>
            {diff != null && <b className={diff === 0 ? 'text-ok' : 'text-bad'}>اختلاف: {fmtCell('money', diff)} {diff === 0 ? '— متعادل' : ''}</b>}
          </div>
          <Card title="تاریخچه">
            {(hist.data ?? []).length === 0 ? <p className="text-mut">هنوز مغایرت‌گیری ثبت نشده است.</p> : (
              <ul className="flex flex-col gap-1">
                {hist.data!.map(h => (
                  <li key={h.id} className="flex items-center gap-3">
                    <span>{fmtCell('date', h.created_at)}</span><span>صورت‌حساب {fmtCell('money', h.statement_balance)}</span>
                    <span className={h.balanced ? 'text-ok' : 'text-bad'}>{h.balanced ? 'متعادل' : `اختلاف ${fmtCell('money', h.difference)}`}</span>
                    {Number(h.id) === lastId && <Btn variant="danger" onClick={() => window.confirm('آخرین مغایرت‌گیری برگردانده شود؟') && run('بازگشت مغایرت‌گیری', () => send(`/bank-accounts/${bid}/reconciliations/${h.id}`, undefined, 'DELETE'))}>بازگشت</Btn>}
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </section>
  )
}
