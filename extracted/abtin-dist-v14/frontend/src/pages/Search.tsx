import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { get, send } from '../lib/api'
import { fmtCell, faDigits } from '../lib/fa'
import type { Kind } from '../lib/types'
import { Btn, Card, Empty, ErrorBox, Spinner } from '../components/ui'

type GlobalRes = { results: Record<string, { label: string; page: string; items: { title: string; sub?: string }[] }> }
type SchemaField = { name: string; ops: string[] }
type Schema = Record<string, { label: string; fields: SchemaField[]; sort: string[] }>
type Filter = { field: string; op: string; value: unknown }
type Saved = { id: number; name: string; shared?: boolean; mine?: boolean; entity: string; query: { q?: string; filters?: Filter[]; sort?: string | null; order?: string } }
type AdvRes = { total: number; columns: { key: string; label: string; kind?: string }[]; rows: Record<string, unknown>[] }

const OPL: Record<string, string> = { eq: 'برابر', ne: 'نابرابر', contains: 'شامل', starts: 'شروع با', gt: 'بزرگ‌تر', gte: 'بزرگ‌تر یا مساوی', lt: 'کوچک‌تر', lte: 'کوچک‌تر یا مساوی', in: 'یکی از', between: 'بین', isnull: 'خالی' }
const PAGE_SIZE = 25
const kindOf = (k?: string): Kind | undefined => (k === 'money' || k === 'bool' || k === 'date' ? k : k === 'qty' ? 'num' : undefined)
const parseValue = (op: string, raw: string): unknown => (op === 'in' || op === 'between' ? raw.split(',').map(x => x.trim()).filter(Boolean) : op === 'isnull' ? true : raw)

function GlobalResults({ q }: { q: string }) {
  const r = useQuery({ queryKey: ['search-global', q], enabled: q.length > 0, queryFn: () => get<GlobalRes>(`/search/global?q=${encodeURIComponent(q)}`) })
  if (!q) return null
  if (r.isLoading) return <Spinner />
  if (r.error) return <ErrorBox error={r.error} />
  const groups = Object.entries(r.data?.results ?? {}).filter(([, v]) => v.items.length)
  if (!groups.length) return <Empty>نتیجه‌ای یافت نشد</Empty>
  return (
    <div className="flex flex-col gap-3">
      {groups.map(([k, v]) => (
        <Card key={k} title={`${v.label} (${faDigits(v.items.length)})`}>
          <ul>{v.items.map((x, i) => (
            <li key={i} className="border-t border-bd py-1 first:border-0 ">
              <Link className="block" to={`/${v.page}`}>{x.title}{x.sub && <small className="ms-2 text-mut">{x.sub}</small>}</Link>
            </li>
          ))}</ul>
        </Card>
      ))}
    </div>
  )
}

function Advanced() {
  const qc = useQueryClient()
  const schema = useQuery({ queryKey: ['search-schema'], queryFn: () => get<Schema>('/search/schema'), staleTime: 300_000 })
  const [entity, setEntity] = useState(''), [q, setQ] = useState(''), [filters, setFilters] = useState<Filter[]>([])
  const [sort, setSort] = useState<string | null>(null), [order, setOrder] = useState('desc'), [page, setPage] = useState(1)
  const [submitted, setSubmitted] = useState<null | { entity: string; q: string; filters: Filter[]; sort: string | null; order: string; page: number }>(null)
  const keys = Object.keys(schema.data ?? {})
  const ent = entity && schema.data?.[entity] ? entity : keys[0] ?? ''
  const sp = schema.data?.[ent]
  const saved = useQuery({ queryKey: ['search-saved', ent], enabled: !!ent, queryFn: () => get<Saved[]>(`/search/saved?entity=${ent}`).catch(() => [] as Saved[]) })
  const result = useQuery({
    queryKey: ['search-adv', submitted], enabled: !!submitted,
    queryFn: () => send<AdvRes>('/search/advanced', { ...submitted, page_size: PAGE_SIZE }),
  })
  const save = useMutation({
    mutationFn: (name: string) => send('/search/saved', { entity: ent, name, query: { q, filters, sort, order } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['search-saved', ent] }),
  })
  const remove = useMutation({
    mutationFn: (id: number) => send(`/search/saved/${id}`, undefined, 'DELETE'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['search-saved', ent] }),
  })
  if (schema.isLoading) return <Spinner />
  if (schema.error) return <ErrorBox error={schema.error} />
  if (!keys.length || !sp) return <Empty>به هیچ بخش قابل‌جستجویی دسترسی ندارید</Empty>
  const run = (p = 1, s = sort, o = order) => { setPage(p); setSubmitted({ entity: ent, q, filters, sort: s, order: o, page: p }) }
  const setF = (i: number, patch: Partial<Filter>) => setFilters(fs => fs.map((f, j) => (j === i ? { ...f, ...patch } : f)))
  const changeField = (i: number, name: string) => setF(i, { field: name, op: sp.fields.find(x => x.name === name)?.ops[0] ?? 'eq', value: '' })
  const pages = Math.max(1, Math.ceil((result.data?.total ?? 0) / PAGE_SIZE))
  const apply = (s: Saved) => {
    const f = s.query.filters ?? []
    setQ(s.query.q ?? ''); setFilters(f); setSort(s.query.sort ?? null); setOrder(s.query.order ?? 'desc')
    setPage(1); setSubmitted({ entity: s.entity, q: s.query.q ?? '', filters: f, sort: s.query.sort ?? null, order: s.query.order ?? 'desc', page: 1 })
  }
  return (
    <div className="flex flex-col gap-3">
      <Card>
        <div className="grid gap-2 sm:grid-cols-4">
          <label className="flex flex-col gap-1">بخش
            <select className="inp" value={ent} onChange={e => { setEntity(e.target.value); setFilters([]); setSort(null); setSubmitted(null) }}>
              {keys.map(k => <option key={k} value={k}>{schema.data![k].label}</option>)}
            </select></label>
          <label className="flex flex-col gap-1">متن<input className="inp" value={q} onChange={e => setQ(e.target.value)} /></label>
          <label className="flex flex-col gap-1">مرتب‌سازی
            <select className="inp" value={sort ?? ''} onChange={e => setSort(e.target.value || null)}>
              <option value="">پیش‌فرض</option>{sp.sort.map(k => <option key={k} value={k}>{k}</option>)}
            </select></label>
          <label className="flex flex-col gap-1">ترتیب
            <select className="inp" value={order} onChange={e => setOrder(e.target.value)}><option value="desc">نزولی</option><option value="asc">صعودی</option></select></label>
        </div>
        <div className="mt-3 flex flex-col gap-2">
          {filters.map((f, i) => {
            const fd = sp.fields.find(x => x.name === f.field) ?? sp.fields[0]
            return (
              <div key={i} className="flex flex-wrap gap-2">
                <select aria-label="فیلد" className="inp w-auto" value={fd.name} onChange={e => changeField(i, e.target.value)}>{sp.fields.map(x => <option key={x.name} value={x.name}>{x.name}</option>)}</select>
                <select aria-label="عملگر" className="inp w-auto" value={f.op} onChange={e => setF(i, { op: e.target.value, value: e.target.value === 'isnull' ? true : '' })}>{fd.ops.map(o => <option key={o} value={o}>{OPL[o] ?? o}</option>)}</select>
                <input aria-label="مقدار" className="inp w-auto" disabled={f.op === 'isnull'} value={Array.isArray(f.value) ? f.value.join(',') : String(f.value === true || f.value == null ? '' : f.value)} onChange={e => setF(i, { value: parseValue(f.op, e.target.value) })} />
                <Btn type="button" variant="ghost" aria-label="حذف شرط" onClick={() => setFilters(fs => fs.filter((_, j) => j !== i))}>×</Btn>
              </div>
            )
          })}
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Btn type="button" variant="ghost" onClick={() => setFilters(fs => [...fs, { field: sp.fields[0].name, op: sp.fields[0].ops[0], value: '' }])}>+ شرط</Btn>
          <Btn type="button" onClick={() => run(1)}>جستجو</Btn>
          <Btn type="button" variant="ghost" disabled={save.isPending} onClick={() => { const n = window.prompt('نام فیلتر:'); if (n) save.mutate(n) }}>ذخیرهٔ فیلتر</Btn>
        </div>
        {save.error != null && <ErrorBox error={save.error} />}
        {(saved.data?.length ?? 0) > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {saved.data!.map(s => (
              <span key={s.id} className="inline-flex overflow-hidden rounded border border-bd">
                <button type="button" className="px-2 py-1 text-sm" onClick={() => apply(s)}>{s.name}{s.shared ? ' (اشتراکی)' : ''}</button>
                {s.mine && <button type="button" aria-label="حذف فیلتر ذخیره‌شده" className="px-2 text-sm" onClick={() => { if (window.confirm('حذف فیلتر ذخیره‌شده؟')) remove.mutate(s.id) }}>×</button>}
              </span>
            ))}
          </div>
        )}
      </Card>
      {submitted && (
        <Card>
          {result.isLoading ? <Spinner /> : result.error ? <ErrorBox error={result.error} /> : result.data && (
            <>
              <p className="mb-2 text-sm text-mut">{faDigits(result.data.total)} نتیجه</p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr>{result.data.columns.map(c => (
                    <th key={c.key} className="th"><button type="button" onClick={() => { const o = sort === c.key && order === 'asc' ? 'desc' : 'asc'; setSort(c.key); setOrder(o); run(1, c.key, o) }}>{c.label}</button></th>
                  ))}</tr></thead>
                  <tbody>
                    {result.data.rows.map((row, i) => <tr key={i}>{result.data!.columns.map(c => <td key={c.key} className="td">{fmtCell(kindOf(c.kind), row[c.key])}</td>)}</tr>)}
                    {!result.data.rows.length && <tr><td className="td" colSpan={result.data.columns.length}>نتیجه‌ای نیست</td></tr>}
                  </tbody>
                </table>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <Btn variant="ghost" disabled={page <= 1} onClick={() => run(page - 1)}>قبلی</Btn>
                <span>{faDigits(page)} / {faDigits(pages)}</span>
                <Btn variant="ghost" disabled={page >= pages} onClick={() => run(page + 1)}>بعدی</Btn>
              </div>
            </>
          )}
        </Card>
      )}
    </div>
  )
}

export default function Search() {
  const [params] = useSearchParams()
  const q = (params.get('q') ?? '').trim()
  const [advanced, setAdvanced] = useState(!q)
  return (
    <section className="mx-auto flex max-w-5xl flex-col gap-4 p-4">
      <div className="flex items-center gap-2">
        <h2 className="me-auto text-lg font-bold">{advanced ? 'جستجوی پیشرفته' : `نتایج جستجو برای «${q}»`}</h2>
        <Btn variant="ghost" onClick={() => setAdvanced(a => !a)}>{advanced ? 'نتایج سراسری' : 'جستجوی پیشرفته'}</Btn>
      </div>
      {advanced ? <Advanced /> : <GlobalResults q={q} />}
    </section>
  )
}
