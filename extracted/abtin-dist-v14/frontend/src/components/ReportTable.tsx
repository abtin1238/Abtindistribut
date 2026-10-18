import { faDigits, faPct, fmtCell, jalaliFull } from '../lib/fa'
import type { Row } from '../lib/types'

export type RCol = { key: string; label: string; kind?: string }
export type RTable = { title: string; columns: RCol[]; rows: Row[]; summary?: [string, unknown, string][] }
const MAX_ROWS = 500
export function cell(kind: string | undefined, v: unknown): string {
  if (v === null || v === undefined || v === '') return '—'
  switch (kind) {
    case 'money': case 'int': return fmtCell('money', v as number)
    case 'qty': return faDigits(Number(v).toLocaleString('en-US', { maximumFractionDigits: 2 }))
    case 'pct': return faPct(v as number)
    case 'date': case 'datetime': return jalaliFull(String(v))
    default: return String(v)
  }
}
export function Summary({ items }: { items?: [string, unknown, string][] }) {
  if (!items?.length) return null
  return <div className="mb-2 flex flex-wrap gap-2">{items.map(([l, v, k]) => <div key={l} className="rounded border border-bd px-3 py-1 "><small className="block text-mut">{l}</small>{v !== '' && <b>{cell(k, v)}</b>}</div>)}</div>
}
export function ReportTable({ t, onRow }: { t: RTable; onRow?: (r: Row) => void }) {
  const rows = t.rows.slice(0, MAX_ROWS)
  return (
    <>
      <div className="overflow-x-auto"><table className="w-full text-sm">
        <thead><tr>{t.columns.map(c => <th key={c.key} className="th">{c.label}</th>)}</tr></thead>
        <tbody>{rows.length ? rows.map((r, i) => (
          <tr key={i} tabIndex={onRow ? 0 : undefined} className={onRow ? 'cursor-pointer hover:bg-ctl ' : undefined}
            onClick={onRow ? () => onRow(r) : undefined} onKeyDown={onRow ? e => { if (e.key === 'Enter') onRow(r) } : undefined}>
            {t.columns.map(c => <td key={c.key} className="td">{cell(c.kind, r[c.key])}</td>)}
          </tr>
        )) : <tr><td className="td" colSpan={t.columns.length}>داده‌ای برای این فیلتر نیست</td></tr>}</tbody>
      </table></div>
      {t.rows.length > MAX_ROWS && <p className="mt-1 text-sm text-mut">فقط ۵۰۰ ردیف اول نمایش داده شد ({faDigits(t.rows.length)} ردیف)؛ برای همهٔ ردیف‌ها خروجی Excel بگیرید.</p>}
    </>
  )
}
