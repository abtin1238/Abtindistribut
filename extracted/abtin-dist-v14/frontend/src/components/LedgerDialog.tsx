import { useQuery } from '@tanstack/react-query'
import { get } from '../lib/api'
import { faMoney, jalaliFull } from '../lib/fa'
import { Btn, ErrorBox, Spinner } from './ui'

type Line = { number: string; date: string; description: string; debit: number | string; credit: number | string; balance: number | string }
export function LedgerTable({ rows }: { rows: Line[] }) {
  return (
    <div className="overflow-x-auto"><table className="w-full text-sm">
      <thead><tr>{['شمارهٔ سند', 'تاریخ', 'شرح', 'بدهکار', 'بستانکار', 'مانده'].map(h => <th key={h} className="th">{h}</th>)}</tr></thead>
      <tbody>{rows.length ? rows.map((x, i) => (
        <tr key={i}><td className="td">{x.number}</td><td className="td">{jalaliFull(x.date)}</td><td className="td whitespace-normal">{x.description}</td>
          <td className="td">{faMoney(x.debit)}</td><td className="td">{faMoney(x.credit)}</td><td className="td">{faMoney(x.balance)}</td></tr>
      )) : <tr><td className="td" colSpan={6}>تراکنشی نیست</td></tr>}</tbody>
    </table></div>
  )
}
export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div role="dialog" aria-modal="true" aria-label={title} className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-t-xl bg-card p-4 sm:rounded-xl">
        <h3 className="mb-3 text-lg font-bold">{title}</h3>{children}
        <div className="mt-3"><Btn variant="ghost" onClick={onClose}>بستن</Btn></div>
      </div>
    </div>
  )
}
export function GeneralLedgerDialog({ code, onClose }: { code: string; onClose: () => void }) {
  const q = useQuery({ queryKey: ['gl', code], queryFn: () => get<{ account: { code: string; name: string }; rows: Line[]; closing: number | string }>(`/reports/general-ledger?account_code=${encodeURIComponent(code)}`) })
  return (
    <Modal title={q.data ? `دفتر کل — ${q.data.account.code} ${q.data.account.name}` : 'دفتر کل'} onClose={onClose}>
      {q.isLoading ? <Spinner /> : q.error ? <ErrorBox error={q.error} /> : q.data && (<><LedgerTable rows={q.data.rows.slice(-200)} /><p className="mt-2">مانده پایان: <b>{faMoney(q.data.closing)}</b></p></>)}
    </Modal>
  )
}
