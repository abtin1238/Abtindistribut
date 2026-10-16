import { useQuery } from '@tanstack/react-query'
import { get } from '../lib/api'
import type { Field, Opt, Row } from '../lib/types'
export function FieldInput({ f, value, onChange }: { f: Field; value: unknown; onChange: (v: unknown) => void }) {
  const remote = useQuery({
    queryKey: ['opts', f.optionsFrom?.endpoint], enabled: !!f.optionsFrom, staleTime: 60_000,
    queryFn: () => get<(Row | string)[]>(f.optionsFrom!.endpoint),
  })
  const opts: Opt[] = f.options ?? (remote.data ?? []).map((r: Row | string) => typeof r === 'string' ? { value: r, label: r } : { value: r[f.optionsFrom?.value ?? 'id'], label: String(r[f.optionsFrom?.label ?? 'name'] ?? r.id) })
  const id = `f-${f.name}`
  if (f.type === 'checkbox')
    return <label className="flex items-center gap-2"><input type="checkbox" checked={!!value} onChange={e => onChange(e.target.checked)} />{f.label}</label>
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id}>{f.label}{f.required && <span className="text-red-500"> *</span>}</label>
      {f.type === 'multi' ? (
        <select id={id} className="inp" multiple size={Math.min(6, Math.max(3, opts.length))} value={((value as string[]) ?? []).map(String)}
          onChange={e => onChange(Array.from(e.target.selectedOptions).map(o => o.value))}>
          {opts.map(o => <option key={String(o.value)} value={String(o.value)}>{o.label}</option>)}
        </select>
      ) : f.type === 'select' ? (
        <select id={id} className="inp" value={String(value ?? '')} onChange={e => onChange(e.target.value)}>
          <option value="">— انتخاب —</option>
          {opts.map(o => <option key={String(o.value)} value={String(o.value)}>{o.label}</option>)}
        </select>
      ) : f.type === 'textarea' ? (
        <textarea id={id} className="inp" rows={3} value={String(value ?? '')} onChange={e => onChange(e.target.value)} />
      ) : (
        <input id={id} className="inp" type={f.type ?? 'text'} inputMode={f.type === 'number' ? 'decimal' : undefined} placeholder={f.placeholder}
          value={String(value ?? '')} onChange={e => onChange(e.target.value)} />
      )}
    </div>
  )
}
/** مقادیر فرم را برای API آماده می‌کند: خالی‌ها حذف، عدد/انتخاب عددی تبدیل می‌شود */
export function cleanValues(fields: Field[], v: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const f of fields) {
    const x = v[f.name]
    if (f.type === 'checkbox') { out[f.name] = !!x; continue }
    if (x === '' || x === undefined || x === null) continue
    if (f.type === 'multi') { const a = (x as string[]).map(y => (f.optionsFrom?.endpoint === '/permissions' || f.optionsFrom?.endpoint === '/webhooks/events' ? y : Number(y))); if (a.length) out[f.name] = a; continue }
    const numeric = f.type === 'number' || (f.type === 'select' && (f.optionsFrom || f.options?.some(o => typeof o.value === 'number')))
    out[f.name] = numeric ? Number(x) : x
  }
  return out
}
export function missing(fields: Field[], v: Record<string, unknown>) {
  return fields.find(f => f.required && !f.hidden && f.type !== 'checkbox' && (v[f.name] === '' || v[f.name] == null))
}
