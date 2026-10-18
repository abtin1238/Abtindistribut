import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { get, send } from '../lib/api'
import type { Row } from '../lib/types'
import { Btn, Card, ErrorBox, Spinner } from '../components/ui'

type L = { account_code: string; side: 'debit' | 'credit'; ratio: string }
const blank = (): L[] => [{ account_code: '', side: 'debit', ratio: '1' }, { account_code: '', side: 'credit', ratio: '1' }]

export default function JournalTemplates() {
  const qc = useQueryClient()
  const list = useQuery({ queryKey: ['journal-templates'], queryFn: () => get<Row[]>('/journal-templates') })
  const accs = useQuery({ queryKey: ['accounts'], queryFn: () => get<Row[]>('/accounts') })
  const postable = (accs.data ?? []).filter(a => (a.level ?? 3) >= 3 && a.active !== false)
  const [name, setName] = useState(''), [desc, setDesc] = useState(''), [lines, setLines] = useState<L[]>(blank())
  const [run, setRun] = useState<{ id: number; amount: string; date: string; description: string } | null>(null)
  const [msg, setMsg] = useState(''), [err, setErr] = useState<unknown>(null)
  async function act(label: string, fn: () => Promise<unknown>) {
    setErr(null); setMsg('')
    try { await fn(); setMsg(`«${label}» انجام شد.`); qc.invalidateQueries({ queryKey: ['journal-templates'] }); qc.invalidateQueries({ queryKey: ['journal'] }) } catch (e) { setErr(e) }
  }
  const sum = (s: string) => lines.filter(l => l.side === s).reduce((a, l) => a + Number(l.ratio || 0), 0)
  const balanced = sum('debit') === sum('credit') && sum('debit') > 0
  const set = (i: number, p: Partial<L>) => setLines(ls => ls.map((l, j) => (j === i ? { ...l, ...p } : l)))
  const valid = name.trim() && balanced && lines.every(l => l.account_code && Number(l.ratio) > 0)
  return (
    <section className="flex flex-col gap-3 p-4">
      <h2 className="text-lg font-bold">قالب‌های سندسازی</h2>
      {msg && <p role="status" className="rounded bg-ok-soft p-2 text-ok ">{msg}</p>}
      {err != null && <ErrorBox error={err} />}
      <Card title="قالب جدید">
        <div className="grid gap-2 sm:grid-cols-2">
          <input aria-label="نام قالب" className="inp" placeholder="نام قالب (مثلاً پرداخت اجاره)" value={name} onChange={e => setName(e.target.value)} />
          <input aria-label="توضیح قالب" className="inp" placeholder="توضیح (اختیاری)" value={desc} onChange={e => setDesc(e.target.value)} />
        </div>
        {lines.map((l, i) => (
          <div key={i} className="mt-2 grid gap-2 sm:grid-cols-[2fr_1fr_1fr_auto]">
            <select aria-label={`حساب ${i + 1}`} className="inp" value={l.account_code} onChange={e => set(i, { account_code: e.target.value })}>
              <option value="">— حساب —</option>{postable.map(a => <option key={a.id} value={a.code}>{a.code} — {a.name}</option>)}
            </select>
            <select aria-label={`سمت ${i + 1}`} className="inp" value={l.side} onChange={e => set(i, { side: e.target.value as L['side'] })}><option value="debit">بدهکار</option><option value="credit">بستانکار</option></select>
            <input aria-label={`ضریب ${i + 1}`} className="inp" type="number" min="0" step="any" value={l.ratio} onChange={e => set(i, { ratio: e.target.value })} />
            <Btn variant="ghost" disabled={lines.length <= 2} onClick={() => setLines(ls => ls.filter((_, j) => j !== i))}>حذف</Btn>
          </div>
        ))}
        <div className="mt-2 flex items-center gap-2">
          <Btn variant="ghost" onClick={() => setLines(ls => [...ls, { account_code: '', side: 'debit', ratio: '1' }])}>+ سطر</Btn>
          <Btn disabled={!valid} onClick={() => act('ذخیره قالب', () => send('/journal-templates', { name: name.trim(), description: desc, lines: lines.map(l => ({ ...l, ratio: Number(l.ratio) })) }).then(() => { setName(''); setDesc(''); setLines(blank()) }))}>ذخیره قالب</Btn>
          {!balanced && <span className="text-sm text-bad">جمع ضرایب بدهکار و بستانکار باید برابر باشد.</span>}
        </div>
      </Card>
      {list.isLoading ? <Spinner /> : list.error ? <ErrorBox error={list.error} /> : (
        <div className="flex flex-col gap-2">
          {(list.data ?? []).length === 0 && <p className="p-4 text-center text-mut">قالبی تعریف نشده است.</p>}
          {list.data!.map(t => {
            const cur = run && run.id === t.id ? run : null
            return (
            <Card key={t.id} title={t.name}>
              {t.description && <p className="text-mut">{t.description}</p>}
              <ul className="my-1 text-sm">{(t.lines as Row[]).map((l, i) => <li key={i}>{l.side === 'debit' ? 'بدهکار' : 'بستانکار'} {l.account_code} × {l.ratio}</li>)}</ul>
              <div className="flex gap-2">
                <Btn onClick={() => setRun({ id: t.id, amount: '', date: '', description: '' })}>ثبت سند از قالب</Btn>
                <Btn variant="danger" onClick={() => window.confirm('قالب حذف شود؟ (اسناد ثبت‌شده تغییری نمی‌کنند)') && act('حذف قالب', () => send(`/journal-templates/${t.id}`, undefined, 'DELETE'))}>حذف</Btn>
              </div>
              {cur && (
                <div className="mt-2 grid gap-2 sm:grid-cols-4">
                  <input aria-label="مبلغ" className="inp" type="number" min="0" inputMode="decimal" placeholder="مبلغ پایه" value={cur.amount} onChange={e => setRun({ ...cur, amount: e.target.value })} />
                  <input aria-label="تاریخ سند" className="inp" type="date" max={new Date().toISOString().slice(0, 10)} value={cur.date} onChange={e => setRun({ ...cur, date: e.target.value })} />
                  <input aria-label="شرح سند" className="inp" placeholder="شرح (اختیاری)" value={cur.description} onChange={e => setRun({ ...cur, description: e.target.value })} />
                  <Btn disabled={!(Number(cur.amount) > 0)} onClick={() => act('ثبت سند', () => send(`/journal-templates/${t.id}/post`, { amount: Number(cur.amount), description: cur.description, ...(cur.date ? { entry_date: cur.date } : {}) }).then(() => setRun(null)))}>ثبت</Btn>
                </div>
              )}
            </Card>
            )
          })}
        </div>
      )}
    </section>
  )
}
