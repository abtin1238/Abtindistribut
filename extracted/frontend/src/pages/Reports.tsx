import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { download, get } from '../lib/api'
import type { Col, Row } from '../lib/types'
import { DataTable } from '../components/DataTable'
import { Btn, ErrorBox, Spinner } from '../components/ui'
import { fmtCell } from '../lib/fa'
type Table = { title: string; columns: { key: string; label: string; kind: string }[]; rows: Row[]; summary?: [string, unknown, string][] }
export const toCols = (t: Table): Col[] => t.columns.map(c => ({ key: c.key, label: c.label, kind: (['money', 'num', 'date'].includes(c.kind) ? c.kind : 'text') as Col['kind'] }))
export default function Reports() {
  const cat = useQuery({ queryKey: ['rep-cat'], queryFn: () => get<{ reports: { name: string; title: string }[] }>('/reports/catalog') })
  const [name, setName] = useState(''), [start, setStart] = useState(''), [end, setEnd] = useState(''), [extra, setExtra] = useState('')
  const [run, setRun] = useState<string | null>(null), [err, setErr] = useState<unknown>(null)
  const qs = () => { const p = new URLSearchParams(extra); if (start) p.set('start', start); if (end) p.set('end', end); return p.toString() }
  const res = useQuery({ queryKey: ['rep', run], enabled: !!run, queryFn: () => get<Table>(`/reports/run/${name}?${run}`) })
  return (
    <section className="flex flex-col gap-3 p-4">
      <h2 className="text-lg font-bold">گزارش‌ها</h2>
      {cat.isLoading ? <Spinner /> : cat.error ? <ErrorBox error={cat.error} /> : (
        <div className="grid gap-2 sm:grid-cols-4">
          <select aria-label="گزارش" className="inp" value={name} onChange={e => { setName(e.target.value); setRun(null) }}>
            <option value="">— گزارش —</option>{cat.data?.reports.map(r => <option key={r.name} value={r.name}>{r.title}</option>)}
          </select>
          <input aria-label="از تاریخ" type="date" className="inp" value={start} onChange={e => setStart(e.target.value)} />
          <input aria-label="تا تاریخ" type="date" className="inp" value={end} onChange={e => setEnd(e.target.value)} />
          <input aria-label="پارامتر اضافه" className="inp" placeholder="مثلاً by=product" value={extra} onChange={e => setExtra(e.target.value)} />
        </div>
      )}
      <div className="flex gap-2">
        <Btn disabled={!name} onClick={() => setRun(qs())}>اجرا</Btn>
        {(['xlsx', 'pdf'] as const).map(f => <Btn key={f} variant="ghost" disabled={!name} onClick={() => download(`/reports/run/${name}/export?format=${f}&${qs()}`, `${name}.${f}`).catch(setErr)}>{f === 'xlsx' ? 'Excel' : 'PDF'}</Btn>)}
      </div>
      {err != null && <ErrorBox error={err} />}
      {run !== null && (res.data ? (
        <>
          <DataTable columns={toCols(res.data)} rows={res.data.rows} />
          {res.data.summary?.map(([l, v, k]) => <p key={l}><b>{l}:</b> {fmtCell(k, v)}</p>)}
        </>
      ) : <DataTable columns={[]} rows={[]} loading={res.isLoading} error={res.error} />)}
    </section>
  )
}
