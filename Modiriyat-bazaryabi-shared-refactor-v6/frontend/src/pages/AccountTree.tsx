import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { get, send } from '../lib/api'
import { fmtCell } from '../lib/fa'
import type { Row } from '../lib/types'
import { Btn, Card, ErrorBox, Spinner } from '../components/ui'

const LEVEL = ['', 'گروه', 'کل', 'معین', 'تفصیلی']
const TYPES: [string, string][] = [['asset', 'دارایی'], ['liability', 'بدهی'], ['equity', 'سرمایه'], ['revenue', 'درآمد'], ['expense', 'هزینه']]

function Node({ n, depth, onAct }: { n: Row; depth: number; onAct: (label: string, fn: () => Promise<unknown>) => void }) {
  const [open, setOpen] = useState(depth < 2)
  const kids: Row[] = n.children ?? []
  return (
    <li>
      <div className={`tree-row tree-indent-${Math.min(depth, 12)}`}>
        {kids.length ? <button aria-label={open ? 'بستن' : 'باز کردن'} className="w-5" onClick={() => setOpen(o => !o)}>{open ? '▾' : '◂'}</button> : <span className="w-5" />}
        <span className="font-mono text-mut">{n.code}</span>
        <span className={n.active ? '' : 'text-mut line-through'}>{n.name}</span>
        <span className="rounded bg-ctl px-1 text-xs ">{LEVEL[n.level]}</span>
        <span className="ms-auto">{fmtCell('money', kids.length ? n.total_balance : n.balance)}</span>
        <Btn variant="ghost" onClick={() => { const name = window.prompt('نام جدید حساب', n.name); if (name && name.trim() && name !== n.name) onAct('تغییر نام', () => send(`/accounts/${n.id}`, { name }, 'PATCH')) }}>تغییر نام</Btn>
        {n.level >= 3 && <Btn variant="ghost" onClick={() => onAct(n.active ? 'غیرفعال‌سازی' : 'فعال‌سازی', () => send(`/accounts/${n.id}`, { active: !n.active }, 'PATCH'))}>{n.active ? 'غیرفعال' : 'فعال'}</Btn>}
      </div>
      {open && kids.length > 0 && <ul>{kids.map(k => <Node key={k.id} n={k} depth={depth + 1} onAct={onAct} />)}</ul>}
    </li>
  )
}

export default function AccountTree() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['accounts-tree'], queryFn: () => get<Row[]>('/accounts/tree') })
  const [f, setF] = useState({ code: '', name: '', type: 'asset', parent_code: '' }), [msg, setMsg] = useState(''), [err, setErr] = useState<unknown>(null)
  async function act(label: string, fn: () => Promise<unknown>) {
    setErr(null); setMsg('')
    try { await fn(); setMsg(`«${label}» انجام شد.`); qc.invalidateQueries({ queryKey: ['accounts-tree'] }); qc.invalidateQueries({ queryKey: ['accounts'] }) } catch (e) { setErr(e) }
  }
  return (
    <section className="flex flex-col gap-3 p-4">
      <h2 className="text-lg font-bold">درخت حساب‌ها</h2>
      <Card title="حساب جدید">
        <div className="grid gap-2 sm:grid-cols-5">
          <input aria-label="کد" className="inp" placeholder="کد (۳ تا ۱۰ رقم)" inputMode="numeric" value={f.code} onChange={e => setF({ ...f, code: e.target.value })} />
          <input aria-label="نام" className="inp" placeholder="نام حساب" value={f.name} onChange={e => setF({ ...f, name: e.target.value })} />
          <select aria-label="نوع" className="inp" value={f.type} onChange={e => setF({ ...f, type: e.target.value })}>{TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
          <input aria-label="کد والد" className="inp" placeholder="کد والد (اختیاری)" inputMode="numeric" value={f.parent_code} onChange={e => setF({ ...f, parent_code: e.target.value })} />
          <Btn disabled={!f.code || !f.name.trim()} onClick={() => act('افزودن حساب', () => send('/accounts', { code: f.code, name: f.name.trim(), type: f.type, ...(f.parent_code ? { parent_code: f.parent_code } : {}) }).then(() => setF({ ...f, code: '', name: '' })))}>افزودن</Btn>
        </div>
        <p className="mt-2 text-xs text-mut">کد حساب باید با کد والد شروع شود و نوعش با والد یکسان باشد. ثبت سند فقط روی معین و تفصیلی ممکن است.</p>
      </Card>
      {msg && <p role="status" className="rounded bg-ok-soft p-2 text-ok ">{msg}</p>}
      {err != null && <ErrorBox error={err} />}
      {q.isLoading ? <Spinner /> : q.error ? <ErrorBox error={q.error} /> : <ul>{q.data!.map(n => <Node key={n.id} n={n} depth={0} onAct={act} />)}</ul>}
    </section>
  )
}
