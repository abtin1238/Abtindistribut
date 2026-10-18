import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { fmtCell } from '../lib/fa'
import { useMe } from '../lib/useMe'
import type { Action, Resource, Row } from '../lib/types'
import { DataTable } from './DataTable'
import { FormDialog } from './FormDialog'
import { Btn } from './ui'
const PAGE = 25
const DEL_MSG = 'این مورد برای همیشه حذف شود؟ این کار قابل بازگشت نیست.'
type Dlg = { kind: 'create' } | { kind: 'action'; a: Action; row: Row } | null
export default function ResourcePage({ r }: { r: Resource }) {
  const qc = useQueryClient(), me = useMe()
  const [page, setPage] = useState(0), [q, setQ] = useState(''), [dlg, setDlg] = useState<Dlg>(null), [flash, setFlash] = useState('')
  const url = r.paged ? `${r.endpoint}${r.endpoint.includes('?') ? '&' : '?'}limit=${PAGE}&offset=${page * PAGE}` : r.endpoint
  const query = useQuery({ queryKey: [r.path, page], queryFn: () => api<Row[]>(url) })
  const all = query.data?.data ?? []
  const filtered = q ? all.filter(x => r.columns.some(c => fmtCell(c.kind, x[c.key]).includes(q) || String(x[c.key] ?? '').includes(q))) : all
  const rows = r.paged ? filtered : filtered.slice(page * PAGE, page * PAGE + PAGE)
  const total = r.paged ? query.data?.total ?? all.length : filtered.length
  const pages = Math.max(1, Math.ceil(total / PAGE))
  const dq = useQuery({ queryKey: ['deletable'], queryFn: () => api<string[]>('/deletable').then(x => x.data), retry: false, staleTime: 300_000 })
  const base = r.endpoint.split('?')[0].replace(/^\//, '')
  const delAct: Action = { label: 'حذف', danger: true, confirm: DEL_MSG, run: row => api(`/${base}/${row.id}`, { method: 'DELETE' }) }
  const acts = dq.data?.includes(base) && !r.actions?.some(a => a.label === 'حذف') ? [...(r.actions ?? []), delAct] : r.actions
  const done = (msg: string) => { setFlash(msg); qc.invalidateQueries({ queryKey: [r.path] }) }
  async function runAction(a: Action, row: Row, v: Record<string, unknown>) { await a.run(row, v); done(`«${a.label}» انجام شد.`) }
  return (
    <section className="p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h2 className="me-auto text-lg font-bold">{r.title}</h2>
        {r.top?.map(t => <Btn key={t.label} variant="ghost" onClick={async () => { try { await t.run(); done(`«${t.label}» انجام شد.`) } catch (e) { setFlash((e as Error).message) } }}>{t.label}</Btn>)}
        {r.newTo && <Link className="rounded bg-bl px-3 py-1.5 text-sm text-white" to={r.newTo}>+ جدید</Link>}
        {r.create && <Btn onClick={() => setDlg({ kind: 'create' })}>+ {r.create.title}</Btn>}
      </div>
      <input aria-label="جستجو" className="inp mb-3" placeholder="جستجو در ردیف‌های این صفحه…" value={q} onChange={e => setQ(e.target.value)} />
      {flash && <p role="status" className="mb-2 rounded bg-ok-soft p-2 text-ok ">{flash}</p>}
      <DataTable columns={r.columns} rows={rows} loading={query.isLoading} error={query.error} empty={r.empty}
        actions={acts && (row => acts.filter(a => !a.when || a.when(row)).map(a => (
          <Btn key={a.label} variant={a.danger ? 'danger' : 'ghost'} onClick={() => (a.fields || a.confirm ? setDlg({ kind: 'action', a, row }) : runAction(a, row, {}).catch(e => setFlash((e as Error).message)))}>{a.label}</Btn>
        )))} />
      <div className="mt-3 flex items-center gap-3">
        <Btn variant="ghost" disabled={page === 0} onClick={() => setPage(p => p - 1)}>قبلی</Btn>
        <span>صفحه {fmtCell('num', page + 1)} از {fmtCell('num', pages)}</span>
        <Btn variant="ghost" disabled={page + 1 >= pages} onClick={() => setPage(p => p + 1)}>بعدی</Btn>
        <span className="ms-auto text-sm text-mut">{fmtCell('num', total)} ردیف</span>
      </div>
      {dlg?.kind === 'create' && r.create && (
        <FormDialog title={r.create.title} fields={r.create.fields} onClose={() => setDlg(null)}
          onSubmit={async v => {
            const body = r.create!.build ? r.create!.build(v, { companyId: me.data?.company.id ?? 0 }) : v
            await api(r.create!.endpoint ?? r.endpoint, { method: r.create!.method ?? 'POST', json: body }); done('ثبت شد.')
          }} />
      )}
      {dlg?.kind === 'action' && (
        <FormDialog title={dlg.a.label} message={dlg.a.confirm} fields={dlg.a.fields ?? []} prefill={dlg.a.prefill?.(dlg.row)} submitLabel="تأیید" onClose={() => setDlg(null)}
          onSubmit={v => runAction(dlg.a, dlg.row, v)} />
      )}
    </section>
  )
}
