import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { get } from '../lib/api'
import { fmtCell } from '../lib/fa'
import type { Col, Row } from '../lib/types'
import { DataTable } from '../components/DataTable'
import { Btn, Card, ErrorBox } from '../components/ui'

const TABS = [['kardex', 'کاردکس کالا'], ['valuation', 'ارزش موجودی'], ['expiring', 'انقضا']] as const
type Tab = typeof TABS[number][0]
const c = (key: string, label: string, kind?: Col['kind']): Col => ({ key, label, kind })

function Kardex() {
  const products = useQuery({ queryKey: ['lookup', '/products'], queryFn: () => get<Row[]>('/products') })
  const whs = useQuery({ queryKey: ['lookup', '/warehouses'], queryFn: () => get<Row[]>('/warehouses') })
  const [pid, setPid] = useState(''), [wid, setWid] = useState(''), [start, setStart] = useState(''), [end, setEnd] = useState(''), [go, setGo] = useState<string | null>(null)
  const qs = () => { const p = new URLSearchParams({ product_id: pid }); if (wid) p.set('warehouse_id', wid); if (start) p.set('start', start); if (end) p.set('end', end); return p.toString() }
  const q = useQuery({ queryKey: ['kardex', go], enabled: go !== null, queryFn: () => get<Row>(`/stock/kardex?${go}`) })
  return (
    <div className="flex flex-col gap-3">
      <div className="grid gap-2 sm:grid-cols-5">
        <select aria-label="کالا" className="inp" value={pid} onChange={e => { setPid(e.target.value); setGo(null) }}><option value="">— کالا —</option>{products.data?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select>
        <select aria-label="انبار" className="inp" value={wid} onChange={e => { setWid(e.target.value); setGo(null) }}><option value="">همه‌ی انبارها</option>{whs.data?.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}</select>
        <input aria-label="از تاریخ" type="date" className="inp" value={start} onChange={e => setStart(e.target.value)} />
        <input aria-label="تا تاریخ" type="date" className="inp" value={end} onChange={e => setEnd(e.target.value)} />
        <Btn disabled={!pid} onClick={() => setGo(qs())}>نمایش</Btn>
      </div>
      {q.error != null && <ErrorBox error={q.error} />}
      {q.data && (
        <>
          <div className="grid gap-2 sm:grid-cols-4">
            <Card title="مانده ابتدا"><b>{fmtCell('num', q.data.opening)}</b></Card><Card title="جمع ورود"><b>{fmtCell('num', q.data.total_in)}</b></Card>
            <Card title="جمع خروج"><b>{fmtCell('num', q.data.total_out)}</b></Card><Card title="مانده پایان"><b>{fmtCell('num', q.data.closing)}</b></Card>
          </div>
          {q.data.matches_stock === false && <p role="alert" className="rounded bg-warn-soft p-2 text-warn ">مجموع گردش با موجودی فعلی ({fmtCell('num', q.data.stock_now)}) برابر نیست؛ بررسی لازم است.</p>}
          <DataTable columns={[c('at', 'زمان', 'date'), c('kind', 'نوع'), c('reference', 'مرجع'), c('reason', 'دلیل'), c('user', 'کاربر'), c('qty_in', 'ورود', 'num'), c('qty_out', 'خروج', 'num'), c('balance', 'مانده', 'num')]} rows={q.data.rows} />
        </>
      )}
    </div>
  )
}

function Valuation() {
  const q = useQuery({ queryKey: ['valuation'], queryFn: () => get<Row>('/reports/stock-valuation') })
  const d = q.data
  return (
    <div className="flex flex-col gap-3">
      {q.error != null && <ErrorBox error={q.error} />}
      {d && (
        <>
          <div className="grid gap-2 sm:grid-cols-3">
            <Card title="ارزش کل موجودی انبار"><b>{fmtCell('money', d.total_value)}</b></Card>
            {d.ledger_balance !== undefined && <Card title="مانده حساب موجودی کالا (۱۳۱۰)"><b>{fmtCell('money', d.ledger_balance)}</b></Card>}
            {d.difference !== undefined && <Card title="اختلاف"><b className={d.reconciled ? 'text-ok' : 'text-bad'}>{fmtCell('money', d.difference)} {d.reconciled ? '— تطبیق دارد' : '— نیاز به بررسی'}</b></Card>}
          </div>
          {d.uncosted_products > 0 && <p role="alert" className="rounded bg-warn-soft p-2 text-warn ">{fmtCell('num', d.uncosted_products)} کالا موجودی دارد ولی بهای میانگین صفر است.</p>}
          <DataTable columns={[c('product', 'کالا'), c('sku', 'کد'), c('quantity', 'موجودی', 'num'), c('reserved', 'رزرو', 'num'), c('avg_cost', 'بهای میانگین', 'money'), c('value', 'ارزش', 'money')]} rows={d.items} />
        </>
      )}
    </div>
  )
}

function Expiring() {
  const [days, setDays] = useState('30')
  const q = useQuery({ queryKey: ['expiring', days], queryFn: () => get<Row>(`/stock/expiring?days=${Number(days) || 0}`) })
  return (
    <div className="flex flex-col gap-3">
      <label className="flex items-center gap-2">تا چند روز آینده<input aria-label="روز" className="inp w-24" type="number" min="0" value={days} onChange={e => setDays(e.target.value)} /></label>
      {q.error != null && <ErrorBox error={q.error} />}
      {q.data && (
        <>
          <p>{fmtCell('num', q.data.expired_count)} بچ منقضی‌شده — ارزش کل: <b>{fmtCell('money', q.data.total_value)}</b></p>
          <DataTable columns={[c('product', 'کالا'), c('warehouse', 'انبار'), c('batch_no', 'بچ'), c('expiry_date', 'انقضا', 'date'), c('days_to_expiry', 'روز مانده', 'num'), c('quantity', 'موجودی', 'num'), c('value', 'ارزش', 'money'), { key: 'status', label: 'وضعیت', render: r => (r.status === 'expired' ? 'منقضی' : 'نزدیک انقضا') }]} rows={q.data.items} empty="بچی در این بازه منقضی نمی‌شود." />
        </>
      )}
    </div>
  )
}

export default function StockReports() {
  const [tab, setTab] = useState<Tab>('kardex')
  return (
    <section className="flex flex-col gap-3 p-4">
      <h2 className="text-lg font-bold">گزارش‌های انبار</h2>
      <div role="tablist" className="flex gap-2">{TABS.map(([k, l]) => <Btn key={k} role="tab" aria-selected={tab === k} variant={tab === k ? 'primary' : 'ghost'} onClick={() => setTab(k)}>{l}</Btn>)}</div>
      {tab === 'kardex' ? <Kardex /> : tab === 'valuation' ? <Valuation /> : <Expiring />}
    </section>
  )
}
