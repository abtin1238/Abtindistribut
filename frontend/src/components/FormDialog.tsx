import { useState } from 'react'
import type { Field } from '../lib/types'
import { Btn, ErrorBox } from './ui'
import { FieldInput, cleanValues, missing } from './FieldInput'
export function FormDialog({ title, fields, onSubmit, onClose, submitLabel = 'ذخیره', message, prefill }: {
  title: string; fields: Field[]; onSubmit: (v: Record<string, unknown>) => Promise<unknown>; onClose: () => void; submitLabel?: string; message?: string; prefill?: Record<string, unknown>
}) {
  const [v, setV] = useState<Record<string, unknown>>(() => Object.fromEntries(fields.map(f => [f.name, prefill?.[f.name] ?? f.def]).filter(([, d]) => d !== undefined && d !== null)))
  const [err, setErr] = useState<unknown>(null), [busy, setBusy] = useState(false)
  async function submit(e: React.FormEvent) {
    e.preventDefault()
    const m = missing(fields, v)
    if (m) return setErr(new Error(`«${m.label}» الزامی است`))
    setBusy(true); setErr(null)
    try { await onSubmit(cleanValues(fields, v)); onClose() } catch (x) { setErr(x) } finally { setBusy(false) }
  }
  return (
    <div role="dialog" aria-modal="true" aria-label={title} className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center">
      <form onSubmit={submit} className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-t-xl bg-card p-4 sm:rounded-xl">
        <h3 className="mb-3 text-lg font-bold">{title}</h3>
        {message && <p className="mb-3">{message}</p>}
        <div className="flex flex-col gap-3">
          {fields.filter(f => !f.hidden).map(f => <FieldInput key={f.name} f={f} value={v[f.name]} onChange={x => setV(s => ({ ...s, [f.name]: x }))} />)}
          {err != null && <ErrorBox error={err} />}
        </div>
        <div className="mt-4 flex gap-2">
          <Btn type="submit" disabled={busy}>{busy ? '…' : submitLabel}</Btn>
          <Btn type="button" variant="ghost" onClick={onClose}>انصراف</Btn>
        </div>
      </form>
    </div>
  )
}
