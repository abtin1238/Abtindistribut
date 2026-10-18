import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { get, send } from '../../lib/api'
import { Btn, Card, ErrorBox, Spinner } from '../ui'

export type Field<T> = { name: keyof T & string; label: string; type?: string; hint?: string }
/** فرم عمومی تنظیمات: GET برای خواندن و PUT برای ذخیره روی یک مسیر. */
export function FormSection<T extends Record<string, unknown>>({ title, path, fields, extra }: { title: string; path: string; fields: Field<T>[]; extra?: (v: Record<string, unknown>) => void }) {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['set', path], queryFn: () => get<T>(path) })
  const [v, setV] = useState<Record<string, unknown>>({}), [msg, setMsg] = useState<unknown>(null), [ok, setOk] = useState(false)
  useEffect(() => { if (q.data) setV(q.data) }, [q.data])
  if (q.isLoading) return <Spinner />
  if (q.error) return <ErrorBox error={q.error} />
  return (
    <Card title={title}>
      <form className="flex flex-col gap-2" onSubmit={async e => {
        e.preventDefault(); setMsg(null); setOk(false)
        try {
          const body = Object.fromEntries(fields.map(f => [f.name, f.type === 'number' ? Number(v[f.name]) : v[f.name]]))
          await send(path, body, 'PUT'); setOk(true); extra?.(body); qc.invalidateQueries({ queryKey: ['set', path] })
        } catch (x) { setMsg(x) }
      }}>
        {fields.map(f => (
          <label key={f.name} className="flex flex-col gap-1">{f.label}
            {f.type === 'textarea'
              ? <textarea className="inp" rows={4} value={String(v[f.name] ?? '')} onChange={e => setV(s => ({ ...s, [f.name]: e.target.value }))} />
              : <input className="inp" type={f.type ?? 'text'} value={String(v[f.name] ?? '')} onChange={e => setV(s => ({ ...s, [f.name]: e.target.value }))} />}
            {f.hint && <small className="text-mut">{f.hint}</small>}
          </label>
        ))}
        {msg != null && <ErrorBox error={msg} />}{ok && <p role="status" className="text-ok">ذخیره شد.</p>}
        <Btn type="submit">ذخیره</Btn>
      </form>
    </Card>
  )
}
