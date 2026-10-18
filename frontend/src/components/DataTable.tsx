import { useState } from 'react'
import type { Col, Row } from '../lib/types'
import { fmtCell } from '../lib/fa'
import { Empty, ErrorBox, Spinner } from './ui'
import { useLookup } from './useLookup'
function RefCell({ id, ref }: { id: unknown; ref: string }) {
  const m = useLookup(ref)
  return <>{id == null ? '—' : m.get(Number(id)) ?? String(id)}</>
}
export function DataTable({ columns, rows, loading, error, empty = 'موردی یافت نشد.', actions }: {
  columns: Col[]; rows: Row[]; loading?: boolean; error?: unknown; empty?: string; actions?: (r: Row) => React.ReactNode
}) {
  const [sort, setSort] = useState<{ key: string; dir: 1 | -1 } | null>(null)
  if (loading) return <Spinner />
  if (error) return <ErrorBox error={error} />
  if (!rows.length) return <Empty>{empty}</Empty>
  const sorted = sort ? [...rows].sort((a, b) => (a[sort.key] > b[sort.key] ? 1 : a[sort.key] < b[sort.key] ? -1 : 0) * sort.dir) : rows
  return (
    <div className="overflow-x-auto rounded border border-bd ">
      <table className="w-full text-sm">
        <thead><tr>
          {columns.map(c => (
            <th key={c.key} className="th" aria-sort={sort?.key === c.key ? (sort.dir === 1 ? 'ascending' : 'descending') : 'none'}>
              <button onClick={() => setSort(s => (s?.key === c.key ? { key: c.key, dir: (-s.dir) as 1 | -1 } : { key: c.key, dir: 1 }))}>{c.label}</button>
            </th>
          ))}
          {actions && <th className="th">عملیات</th>}
        </tr></thead>
        <tbody>
          {sorted.map((r, i) => (
            <tr key={r.id ?? i}>
              {columns.map(c => (
                <td key={c.key} className="td">
                  {c.render ? c.render(r) : c.kind === 'ref' && c.ref ? <RefCell id={r[c.key]} ref={c.ref} /> : fmtCell(c.kind, r[c.key])}
                </td>
              ))}
              {actions && <td className="td"><div className="flex gap-1">{actions(r)}</div></td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
