import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { get, send } from '../lib/api'
import { Btn, Card, ErrorBox, Spinner } from '../components/ui'
function Section<T extends Record<string, unknown>>({ title, path, fields }: { title: string; path: string; fields: { name: keyof T & string; label: string; type?: string }[] }) {
  const q = useQuery({ queryKey: ['set', path], queryFn: () => get<T>(path) })
  const [v, setV] = useState<Record<string, unknown>>({}), [msg, setMsg] = useState<unknown>(null), [ok, setOk] = useState(false)
  useEffect(() => { if (q.data) setV(q.data) }, [q.data])
  if (q.isLoading) return <Spinner />
  if (q.error) return <ErrorBox error={q.error} />
  return (
    <Card title={title}>
      <form className="flex flex-col gap-2" onSubmit={async e => {
        e.preventDefault(); setMsg(null); setOk(false)
        try { await send(path, Object.fromEntries(fields.map(f => [f.name, f.type === 'number' ? Number(v[f.name]) : v[f.name]])), 'PUT'); setOk(true) } catch (x) { setMsg(x) }
      }}>
        {fields.map(f => (
          <label key={f.name} className="flex flex-col gap-1">{f.label}
            {f.type === 'textarea'
              ? <textarea className="inp" rows={4} value={String(v[f.name] ?? '')} onChange={e => setV(s => ({ ...s, [f.name]: e.target.value }))} />
              : <input className="inp" type={f.type ?? 'text'} value={String(v[f.name] ?? '')} onChange={e => setV(s => ({ ...s, [f.name]: e.target.value }))} />}
          </label>
        ))}
        {msg != null && <ErrorBox error={msg} />}{ok && <p role="status" className="text-green-700">ذخیره شد.</p>}
        <Btn type="submit">ذخیره</Btn>
      </form>
    </Card>
  )
}
export default function Settings() {
  return (
    <section className="mx-auto flex max-w-xl flex-col gap-4 p-4">
      <h2 className="text-lg font-bold">تنظیمات</h2>
      <Section title="برند" path="/settings/brand" fields={[{ name: 'name', label: 'نام' }, { name: 'tagline', label: 'شعار' }, { name: 'color', label: 'رنگ برند', type: 'color' }]} />
      <Section title="مالیات" path="/settings/tax" fields={[{ name: 'vat_percent', label: 'درصد ارزش افزوده', type: 'number' }]} />
      <Section title="شرایط فاکتور" path="/settings/invoice-terms" fields={[{ name: 'terms', label: 'متن', type: 'textarea' }]} />
    </section>
  )
}
