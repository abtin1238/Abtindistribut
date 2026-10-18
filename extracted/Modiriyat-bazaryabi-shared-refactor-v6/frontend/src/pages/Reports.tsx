import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { download, get, send } from '../lib/api'
import { faMoney, jalaliFull } from '../lib/fa'
import type { Row } from '../lib/types'
import { Btn, Card, ErrorBox, Spinner } from '../components/ui'
import { LedgerTable, Modal } from '../components/LedgerDialog'
import { ReportTable, Summary, type RTable } from '../components/ReportTable'

type Catalog = { reports: { name: string; title: string }[] }
type Job = { id: number; title?: string; report: string; fmt: string; status: string; error?: string; created_at: string; filename: string }
type Opt = { id: number; name: string }

const SALES_BY: Record<string, string> = { product: 'کالا', customer: 'مشتری', seller: 'فروشنده', region: 'منطقه', branch: 'شعبه', day: 'روز', category: 'دسته‌بندی' }
const PROFIT_BY: Record<string, string> = { product: 'کالا', customer: 'مشتری', seller: 'فروشنده', region: 'منطقه' }
const INV_KIND: Record<string, string> = { stock: 'موجودی و ارزش', low: 'کم‌موجودی', dead: 'کالای راکد', movement: 'گردش کالا' }
const JOB_ST: Record<string, string> = { queued: 'در صف', running: 'در حال ساخت', done: 'آماده', failed: 'ناموفق' }
/** کدام فیلترها برای کدام گزارش معنا دارند */
const USES: Record<string, string[]> = {
  sales: ['by', 'user_id', 'region', 'branch_id'], customers: ['user_id', 'region', 'days'], inventory: ['kind', 'days', 'branch_id'],
  visitors: ['user_id'], drivers: ['user_id'], profit: ['by'], aging: [], finance: [],
}
const PRESET_KEYS = ['by', 'kind', 'days', 'region', 'user_id', 'branch_id', 'start', 'end']
const NO_RANGE = new Set(['aging', 'finance'])
const clean = (p: Record<string, string>) => Object.fromEntries(Object.entries(p).filter(([, v]) => v.trim() !== ''))

function Jobs() {
  const q = useQuery({ queryKey: ['rep-jobs'], queryFn: () => get<Job[]>('/reports/jobs'), refetchInterval: q => (q.state.data?.some(j => j.status === 'queued' || j.status === 'running') ? 2500 : false) })
  const [err, setErr] = useState<unknown>(null)
  return (
    <Card title="خروجی‌های پس‌زمینه">
      <Btn variant="ghost" className="mb-2" onClick={() => q.refetch()}>به‌روزرسانی</Btn>
      {q.isLoading ? <Spinner /> : q.error ? <ErrorBox error={q.error} /> : !q.data?.length
        ? <p className="text-mut">هنوز خروجی‌ای نساخته‌اید. برای گزارش‌های بزرگ از «ساخت در پس‌زمینه» استفاده کنید.</p>
        : (
          <div className="overflow-x-auto"><table className="w-full text-sm">
            <thead><tr>{['گزارش', 'قالب', 'وضعیت', 'زمان', ''].map(h => <th key={h} className="th">{h}</th>)}</tr></thead>
            <tbody>{q.data.map(j => (
              <tr key={j.id}><td className="td">{j.title || j.report}</td><td className="td">{j.fmt}</td>
                <td className="td">{JOB_ST[j.status] ?? j.status}{j.error && <small className="block text-bad">{j.error}</small>}</td>
                <td className="td">{jalaliFull(j.created_at)}</td>
                <td className="td">{j.status === 'done' && <Btn variant="ghost" onClick={() => download(`/reports/jobs/${j.id}/download`, j.filename).catch(setErr)}>دانلود</Btn>}</td></tr>
            ))}</tbody></table></div>
        )}
      {err != null && <ErrorBox error={err} />}
    </Card>
  )
}

export default function Reports() {
  const [sp] = useSearchParams(), qc = useQueryClient()
  const cat = useQuery({ queryKey: ['rep-cat'], queryFn: () => get<Catalog>('/reports/catalog') })
  const users = useQuery({ queryKey: ['rep-users'], queryFn: () => get<Opt[]>('/users').catch(() => [] as Opt[]), staleTime: 300_000 })
  const branches = useQuery({ queryKey: ['rep-branches'], queryFn: () => get<{ branches?: Opt[] }>('/organizations').then(r => r.branches ?? []).catch(() => [] as Opt[]), staleTime: 300_000 })
  const preset = useMemo(() => Object.fromEntries(PRESET_KEYS.filter(k => sp.get(k)).map(k => [k, sp.get(k)!])), [sp])
  const [name, setName] = useState(sp.get('name') ?? '')
  const [p, setP] = useState<Record<string, string>>({ days: '60', ...preset })
  const [applied, setApplied] = useState<null | { name: string; params: Record<string, string> }>(sp.get('name') ? { name: sp.get('name')!, params: clean({ days: '60', ...preset }) } : null)
  const [err, setErr] = useState<unknown>(null), [modal, setModal] = useState<null | { title: string; body: React.ReactNode }>(null)
  useEffect(() => { if (!name && cat.data?.reports[0]) setName(cat.data.reports[0].name) }, [cat.data, name])
  const uses = USES[name] ?? [], used = (k: string) => uses.includes(k)
  const range = !NO_RANGE.has(name) || name === 'aging'
  const set = (k: string, v: string) => setP(s => ({ ...s, [k]: v }))
  const params = () => {
    const keep = new Set([...uses, ...(range ? ['start', 'end'] : [])])
    return clean(Object.fromEntries(Object.entries(p).filter(([k]) => keep.has(k))))
  }
  const qs = (extra: Record<string, string> = {}) => new URLSearchParams({ ...params(), ...extra }).toString()
  const res = useQuery({ queryKey: ['rep', applied], enabled: !!applied, queryFn: () => get<RTable>(`/reports/run/${applied!.name}?${new URLSearchParams(applied!.params).toString()}`) })
  const queue = useMutation({
    mutationFn: (format: 'xlsx' | 'pdf') => send('/reports/jobs', { report: name, format, params: params() }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rep-jobs'] }),
  })
  const canDrill = applied && ['sales', 'customers', 'aging'].includes(applied.name)
  async function drill(r: Row) {
    if (!applied) return
    try {
      if (applied.name === 'sales') {
        const d = await get<RTable>(`/reports/sales/detail?${new URLSearchParams({ ...applied.params, by: applied.params.by ?? '', key: String(r._key ?? '') }).toString()}`)
        setModal({ title: `سفارش‌های «${r.name}»`, body: <><Summary items={d.summary} /><ReportTable t={d} /></> })
      } else {
        const d = await get<{ customer: { name: string }; rows: Parameters<typeof LedgerTable>[0]['rows']; balance: number }>(`/customers/${encodeURIComponent(String(r._key))}/ledger`)
        setModal({ title: `ریز حساب ${d.customer.name}`, body: <><LedgerTable rows={d.rows} /><p className="mt-2">مانده: <b>{faMoney(d.balance)}</b></p></> })
      }
    } catch (x) { setErr(x) }
  }
  const select = (k: string, label: string, opts: [string, string][], all = false) => (
    <label className="flex flex-col gap-1">{label}
      <select className="inp" value={p[k] ?? ''} onChange={e => set(k, e.target.value)}>{all && <option value="">همه</option>}{opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
  )
  return (
    <section className="mx-auto flex max-w-6xl flex-col gap-3 p-4">
      <h2 className="text-lg font-bold">گزارش‌ها</h2>
      <p className="text-sm text-mut">گزارش‌های مدیریتی با فیلتر پیشرفته و خروجی Excel / PDF. با کلیک روی ردیف فروش، مشتریان و بدهکاران وارد جزئیات شوید.</p>
      {cat.isLoading ? <Spinner /> : cat.error ? <ErrorBox error={cat.error} /> : (
        <div role="tablist" aria-label="گزارش‌ها" className="flex flex-wrap gap-2">
          {cat.data?.reports.map(r => <button key={r.name} role="tab" aria-selected={r.name === name} onClick={() => { setName(r.name); setApplied(null) }}
            className={`rounded border px-3 py-1 text-sm ${r.name === name ? 'border-bl bg-bl text-white' : 'border-bd'}`}>{r.title}</button>)}
        </div>
      )}
      <Card>
        <div className="grid gap-2 sm:grid-cols-4">
          {range && <><label className="flex flex-col gap-1">{name === 'aging' ? 'تا تاریخ' : 'از تاریخ'}<input type="date" className="inp" value={name === 'aging' ? p.end ?? '' : p.start ?? ''} onChange={e => set(name === 'aging' ? 'end' : 'start', e.target.value)} /></label>
            {name !== 'aging' && <label className="flex flex-col gap-1">تا تاریخ<input type="date" className="inp" value={p.end ?? ''} onChange={e => set('end', e.target.value)} /></label>}</>}
          {used('by') && select('by', 'مبنا', Object.entries(name === 'profit' ? PROFIT_BY : SALES_BY))}
          {used('kind') && select('kind', 'نوع گزارش', Object.entries(INV_KIND))}
          {used('days') && <label className="flex flex-col gap-1">روز (راکد/غیرفعال)<input type="number" min={1} max={3650} className="inp" value={p.days ?? ''} onChange={e => set('days', e.target.value)} /></label>}
          {used('region') && <label className="flex flex-col gap-1">منطقه<input maxLength={60} className="inp" value={p.region ?? ''} onChange={e => set('region', e.target.value)} /></label>}
          {used('user_id') && select('user_id', 'کاربر', (users.data ?? []).map(u => [String(u.id), u.name]), true)}
          {used('branch_id') && select('branch_id', 'شعبه', (branches.data ?? []).map(b => [String(b.id), b.name]), true)}
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Btn disabled={!name} onClick={() => setApplied({ name, params: params() })}>نمایش گزارش</Btn>
          {(['xlsx', 'pdf'] as const).map(f => <Btn key={f} variant="ghost" disabled={!name} onClick={() => download(`/reports/run/${name}/export?${qs({ format: f })}`, `${name}.${f}`).catch(setErr)}>{f === 'xlsx' ? 'Excel' : 'PDF'}</Btn>)}
          {(['xlsx', 'pdf'] as const).map(f => <Btn key={`q${f}`} variant="ghost" disabled={!name || queue.isPending} onClick={() => queue.mutate(f)}>ساخت {f === 'xlsx' ? 'Excel' : 'PDF'} در پس‌زمینه</Btn>)}
        </div>
        {queue.error != null && <ErrorBox error={queue.error} />}
      </Card>
      {err != null && <ErrorBox error={err} />}
      {applied && (res.isLoading ? <Spinner /> : res.error ? <ErrorBox error={res.error} /> : res.data && (
        <Card title={res.data.title}><Summary items={res.data.summary} /><ReportTable t={res.data} onRow={canDrill ? drill : undefined} /></Card>
      ))}
      <Jobs />
      {modal && <Modal title={modal.title} onClose={() => setModal(null)}>{modal.body}</Modal>}
    </section>
  )
}
