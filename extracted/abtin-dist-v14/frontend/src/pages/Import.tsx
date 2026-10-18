import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, get } from '../lib/api'
import { faDigits } from '../lib/fa'
import { Btn, Card, ErrorBox, Spinner } from '../components/ui'

type Col = { index: number; header: string; field: string; auto?: boolean }
type FieldDef = { key: string; label: string; required: boolean }
type RowRes = { line: number; status: string; label: string; messages: string[]; changes: { field: string; old: string; new: string }[] }
type Res = {
  file: string; sheet: string; sheets: string[]; header_row: number; detected_entity: string; entity: string; entities: Record<string, string>
  applied: boolean; sample: string[][]; columns: Col[]; fields: FieldDef[]
  summary: { new: number; update: number; unchanged: number; error: number; total: number; skipped: number } | null
  rows: RowRes[]; errors: RowRes[]; issues: string[]
}
const STATUS: Record<string, string> = { new: 'جدید', update: 'به‌روزرسانی', unchanged: 'بدون تغییر', error: 'خطا' }
const NEEDS_WAREHOUSE = new Set(['products', 'stock'])

export default function Import() {
  const [file, setFile] = useState<File | null>(null)
  const [entity, setEntity] = useState(''), [sheet, setSheet] = useState(''), [headerRow, setHeaderRow] = useState<number | ''>('')
  const [warehouse, setWarehouse] = useState(''), [mapping, setMapping] = useState<Record<number, string> | null>(null), [strict, setStrict] = useState(false)
  const [res, setRes] = useState<Res | null>(null), [busy, setBusy] = useState(false), [err, setErr] = useState<unknown>(null)
  const warehouses = useQuery({ queryKey: ['import-warehouses'], queryFn: () => get<{ id: number; name: string }[]>('/warehouses').catch(() => []) })

  const form = (commit: boolean, over: { entity?: string; sheet?: string; headerRow?: number | ''; mapping?: Record<number, string> | null } = {}) => {
    const e = over.entity ?? entity, sh = over.sheet ?? sheet, hr = over.headerRow ?? headerRow, mp = over.mapping === undefined ? mapping : over.mapping
    const f = new FormData()
    f.append('file', file!)
    if (e) f.append('entity', e)
    if (sh) f.append('sheet', sh)
    if (hr) f.append('header_row', String(hr))
    if (mp) f.append('mapping', JSON.stringify(Object.fromEntries(Object.entries(mp).filter(([, v]) => v))))
    if (warehouse) f.append('warehouse_id', warehouse)
    if (commit) f.append('strict', strict ? 'true' : 'false')
    return f
  }
  async function run(commit: boolean, over: Parameters<typeof form>[1] = {}) {
    if (!file) return setErr(new Error('ابتدا فایل را انتخاب کنید'))
    if (commit && !window.confirm('داده‌ها در سیستم ثبت می‌شوند. ادامه می‌دهید؟')) return
    setBusy(true); setErr(null)
    try {
      const { data } = await api<Res>(`/import/${commit ? 'commit' : 'preview'}`, { method: 'POST', form: form(commit, over) })
      setRes(data); setEntity(data.entity); setSheet(data.sheet); setHeaderRow(data.header_row)
      setMapping(Object.fromEntries(data.columns.map(c => [c.index, c.field])))
    } catch (x) { setErr(x) } finally { setBusy(false) }
  }
  const pick = (f: File | null) => { setFile(f); setRes(null); setErr(null); setEntity(''); setSheet(''); setHeaderRow(''); setMapping(null) }
  const needsWh = NEEDS_WAREHOUSE.has(entity)

  return (
    <section className="mx-auto flex max-w-5xl flex-col gap-4 p-4">
      <h2 className="text-lg font-bold">ورود اطلاعات</h2>
      <Card>
        <p className="mb-2 text-sm">خروجی هلو یا هر نرم‌افزار دیگر (Excel، CSV، DBF، HTML، XML، JSON، ODS) را انتخاب یا رها کنید. نوع داده و ستون‌ها خودکار تشخیص داده می‌شوند و پیش از ثبت می‌توانید آن‌ها را اصلاح کنید.</p>
        <div onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); pick(e.dataTransfer.files[0] ?? null) }} className="rounded border border-dashed border-bd p-4">
          <input type="file" aria-label="انتخاب فایل برای ورود اطلاعات" onChange={e => pick(e.target.files?.[0] ?? null)} />
          {file && <p className="mt-1 text-sm">{file.name}</p>}
        </div>
        <Btn className="mt-2" disabled={busy || !file} onClick={() => run(false)}>پیش‌نمایش</Btn>
      </Card>
      {busy && <Spinner />}
      {err != null && <ErrorBox error={err} />}
      {res && (
        <>
          {res.applied
            ? <p role="status" className="rounded bg-ok-soft p-3 text-ok ">✓ ثبت شد.</p>
            : <p className="rounded bg-ctl p-3 ">پیش‌نمایش (چیزی ثبت نشده است). نوع داده و نگاشت ستون‌ها را بررسی کنید.</p>}
          <Card title={res.file}>
            <div className="flex flex-wrap items-end gap-3">
              <label className="flex flex-col gap-1">نوع داده
                <select className="inp w-auto" value={entity} disabled={busy || res.applied} onChange={e => { setEntity(e.target.value); setMapping(null); run(false, { entity: e.target.value, mapping: null }) }}>
                  <option value="">— انتخاب —</option>{Object.entries(res.entities).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
                </select></label>
              {res.sheets.length > 1 && (
                <label className="flex flex-col gap-1">برگه
                  <select className="inp w-auto" value={sheet} disabled={busy || res.applied} onChange={e => { setSheet(e.target.value); run(false, { sheet: e.target.value, mapping: null }) }}>
                    {res.sheets.map(n => <option key={n}>{n}</option>)}</select></label>
              )}
              <label className="flex flex-col gap-1">سطر سرستون
                <input className="inp w-24" type="number" min={1} value={headerRow} disabled={res.applied} onChange={e => setHeaderRow(e.target.value ? Number(e.target.value) : '')}
                  onBlur={() => run(false, { mapping: null })} /></label>
              {needsWh && (
                <label className="flex flex-col gap-1">انبار (برای موجودی)
                  <select className="inp w-auto" value={warehouse} disabled={res.applied} onChange={e => setWarehouse(e.target.value)}>
                    <option value="">پیش‌فرض</option>{warehouses.data?.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}</select></label>
              )}
            </div>
            {res.issues.map((m, i) => <p key={i} role="alert" className="mt-2 text-bad">{m}</p>)}
          </Card>
          {res.columns.length > 0 && res.fields.length > 0 && (
            <Card title="نگاشت ستون‌ها">
              <div className="overflow-x-auto"><table className="w-full text-sm">
                <thead><tr><th className="th">ستون فایل</th><th className="th">فیلد سیستم</th></tr></thead>
                <tbody>{res.columns.map(c => (
                  <tr key={c.index}><td className="td">{c.header || `ستون ${faDigits(c.index + 1)}`}</td>
                    <td className="td"><select className="inp w-auto" aria-label={`فیلد برای ${c.header}`} disabled={res.applied} value={mapping?.[c.index] ?? c.field}
                      onChange={e => setMapping(m => ({ ...(m ?? {}), [c.index]: e.target.value }))}>
                      <option value="">— نادیده —</option>{res.fields.map(f => <option key={f.key} value={f.key}>{f.label}{f.required ? ' *' : ''}</option>)}</select></td></tr>
                ))}</tbody></table></div>
              {!res.applied && <Btn className="mt-2" variant="ghost" disabled={busy} onClick={() => run(false)}>اعمال نگاشت و بازبینی</Btn>}
            </Card>
          )}
          {res.summary && (
            <Card title="خلاصه">
              <p>جدید: <b>{faDigits(res.summary.new)}</b> | به‌روزرسانی: <b>{faDigits(res.summary.update)}</b> | بدون تغییر: {faDigits(res.summary.unchanged)} | خطا: <b className="text-bad">{faDigits(res.summary.error)}</b> | ردیف نادیده: {faDigits(res.summary.skipped)} | جمع: {faDigits(res.summary.total)}</p>
              {res.rows.length < res.summary.total && <p className="text-sm text-mut">فقط {faDigits(res.rows.length)} ردیف اول نمایش داده می‌شود.</p>}
            </Card>
          )}
          {res.errors.length > 0 && (
            <Card title={`خطاها (${faDigits(res.errors.length)})`}>{res.errors.map(r => <div key={r.line} className="text-bad">ردیف {faDigits(r.line)} {r.label && `(${r.label})`}: {r.messages.join('، ')}</div>)}</Card>
          )}
          {res.rows.length > 0 && (
            <Card title="ردیف‌ها">
              <div className="max-h-96 overflow-auto"><table className="w-full text-sm">
                <thead><tr><th className="th">ردیف</th><th className="th">عنوان</th><th className="th">وضعیت</th><th className="th">تغییرات</th></tr></thead>
                <tbody>{res.rows.map(r => (
                  <tr key={r.line}><td className="td">{faDigits(r.line)}</td><td className="td">{r.label}</td><td className="td">{STATUS[r.status] ?? r.status}</td>
                    <td className="td whitespace-normal">{[...r.messages, ...r.changes.map(c => `${c.field}: ${c.old || '∅'} ← ${c.new}`)].join(' | ')}</td></tr>
                ))}</tbody></table></div>
            </Card>
          )}
          {!res.applied && res.summary && (
            <div className="flex flex-wrap items-center gap-3">
              <Btn disabled={busy || res.issues.length > 0} onClick={() => run(true)}>ثبت نهایی</Btn>
              <label className="flex items-center gap-2"><input type="checkbox" checked={strict} onChange={e => setStrict(e.target.checked)} />اگر خطا بود هیچ‌چیز ثبت نشود</label>
            </div>
          )}
        </>
      )}
    </section>
  )
}
