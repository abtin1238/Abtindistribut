import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { send } from '../lib/api'
import type { Field } from '../lib/types'
import { Btn, ErrorBox } from './ui'
import { FieldInput, cleanValues, missing } from './FieldInput'
type V = Record<string, unknown>
export default function DocForm({ title, header, line, endpoint, build, back, then }: {
  title: string; header: Field[]; line: Field[]; endpoint: string; back: string
  build: (h: V, lines: V[]) => unknown
  then?: { label: string; run: (res: any) => Promise<unknown> }
}) {
  const nav = useNavigate()
  const init = (fs: Field[]): V => Object.fromEntries(fs.filter(f => f.def !== undefined).map(f => [f.name, f.def]))
  const [h, setH] = useState<V>(init(header)), [lines, setLines] = useState<V[]>([init(line)])
  const [err, setErr] = useState<unknown>(null), [busy, setBusy] = useState(false)
  async function submit(extra: boolean) {
    setErr(null)
    const bad = missing(header, h) ?? lines.map(l => missing(line, l)).find(Boolean)
    if (bad) return setErr(new Error(`«${bad.label}» الزامی است`))
    setBusy(true)
    try {
      const res = await send(endpoint, build(cleanValues(header, h), lines.map(l => cleanValues(line, l))))
      if (extra && then) await then.run(res)
      nav(back)
    } catch (e) { setErr(e) } finally { setBusy(false) }
  }
  return (
    <section className="mx-auto max-w-3xl p-4">
      <h2 className="mb-3 text-lg font-bold">{title}</h2>
      <div className="grid gap-3 sm:grid-cols-2">{header.map(f => <FieldInput key={f.name} f={f} value={h[f.name]} onChange={x => setH(s => ({ ...s, [f.name]: x }))} />)}</div>
      <h3 className="mb-2 mt-4 font-semibold">اقلام</h3>
      {lines.map((l, i) => (
        <div key={i} className="mb-2 grid items-end gap-2 rounded border border-slate-200 p-2 dark:border-slate-700 sm:grid-cols-[repeat(auto-fit,minmax(9rem,1fr))_auto]">
          {line.map(f => <FieldInput key={f.name} f={{ ...f, name: `${f.name}-${i}` }} value={l[f.name]} onChange={x => setLines(s => s.map((y, j) => (j === i ? { ...y, [f.name]: x } : y)))} />)}
          <Btn type="button" variant="ghost" disabled={lines.length === 1} onClick={() => setLines(s => s.filter((_, j) => j !== i))}>حذف</Btn>
        </div>
      ))}
      <Btn type="button" variant="ghost" onClick={() => setLines(s => [...s, init(line)])}>+ افزودن ردیف</Btn>
      {err != null && <div className="mt-3"><ErrorBox error={err} /></div>}
      <div className="mt-4 flex flex-wrap gap-2">
        <Btn disabled={busy} onClick={() => submit(false)}>{busy ? '…' : 'ثبت'}</Btn>
        {then && <Btn variant="ghost" disabled={busy} onClick={() => submit(true)}>{then.label}</Btn>}
        <Btn variant="ghost" onClick={() => nav(back)}>انصراف</Btn>
      </div>
    </section>
  )
}
