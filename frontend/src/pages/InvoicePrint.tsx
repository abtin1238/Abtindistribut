import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { get } from '../lib/api'
import { faDigits } from '../lib/fa'
import { Btn, ErrorBox, Spinner } from '../components/ui'

type Num = number | string
type Detail = {
  invoice: { number: string; status: string; issued_at: string; subtotal?: Num; total: Num; tax: Num; shipping: Num; returned: Num; paid: Num; note?: string; terms?: string }
  customer: { name: string; code: string; customer_group?: string; region?: string; address?: string; phone?: string }
  company: { name: string; code: string; brand?: { name?: string; tagline?: string; color?: string; logo_url?: string } }
  lines: { description: string; quantity: Num; unit: string; unit_price: Num; discount: Num; line_total: Num }[]
  payments: { amount: Num; method: string }[]
  remaining: Num; seller: string; warehouse: string; order_number: string
}
const ST: Record<string, string> = { open: 'پرداخت‌نشده', partial: 'پرداخت جزئی', paid: 'پرداخت‌شده', cancelled: 'باطل‌شده' }
const METHOD: Record<string, string> = { cash: 'نقد', card: 'کارت', transfer: 'حواله', check: 'چک' }
const fa = (v: Num | null | undefined) => faDigits(Number(v ?? 0).toLocaleString('en-US', { maximumFractionDigits: 2 }))
const dt = (s: string) => new Date(/Z$|[+-]\d\d:?\d\d$/.test(s) ? s : `${s}Z`).toLocaleDateString('fa-IR-u-ca-persian')
/** یادداشت‌های HTMLِ قدیمی به متن ساده تبدیل می‌شوند؛ DOMParser اسکریپتی اجرا نمی‌کند. */
const plain = (h?: string) => new DOMParser().parseFromString(String(h ?? '').replace(/<\/(p|div|li|h\d)>|<br\s*\/?>/gi, '\n'), 'text/html').body.textContent?.trim() ?? ''
const safeUrl = (u?: string) => (u && /^(https?:\/\/|\/)/.test(u) ? u : '')
const Mu = ({ children }: { children: React.ReactNode }) => <span className="text-sm text-slate-500">{children}</span>

export default function InvoicePrint() {
  const { id } = useParams(), nav = useNavigate()
  const q = useQuery({ queryKey: ['invoice-print', id], enabled: !!id && /^\d+$/.test(id), queryFn: () => get<Detail>(`/invoices/${id}`) })
  /* برگهٔ چاپ همیشه روشن است، مستقل از تم پنل */
  useEffect(() => { const prev = document.documentElement.dataset.theme; document.documentElement.dataset.theme = 'light'; return () => { document.documentElement.dataset.theme = prev ?? 'dark' } }, [])
  if (!id || !/^\d+$/.test(id)) return <ErrorBox error={new Error('شناسه فاکتور نامعتبر است')} />
  if (q.isLoading) return <Spinner />
  if (q.error) return <ErrorBox error={q.error} />
  const { invoice: i, customer: c, company: co, lines, payments: pays } = q.data!, b = co.brand ?? {}
  const color = /^#[0-9a-fA-F]{6}$/.test(b.color ?? '') ? b.color : '#2563eb'
  const returned = Number(i.returned ?? 0), remaining = Number(q.data!.remaining)
  const note = plain(i.note), terms = plain(i.terms), logo = safeUrl(b.logo_url)
  document.title = `فاکتور ${i.number}`
  return (
    <div className="min-h-screen bg-slate-100 p-3 print:bg-white print:p-0 dark:bg-slate-900">
      <div className="mx-auto mb-3 flex max-w-3xl gap-2 print:hidden">
        <Btn onClick={() => window.print()}>چاپ / ذخیره PDF</Btn>
        <Btn variant="ghost" onClick={() => (window.history.length > 1 ? nav(-1) : nav('/invoices'))}>بازگشت</Btn>
      </div>
      <main className="mx-auto max-w-3xl overflow-x-auto rounded-lg border border-slate-200 bg-white p-6 text-slate-900 print:max-w-none print:border-0 print:p-0">
        <header className="flex flex-wrap justify-between gap-4 border-b border-slate-200 pb-4" style={{ borderColor: color }}>
          <div className="flex items-center gap-3">
            {logo ? <img alt="" src={logo} className="h-14 w-14 object-contain" /> : <div className="grid h-14 w-14 place-items-center rounded border text-xs text-slate-400">لوگو</div>}
            <div><b>{b.name || co.name}</b><div><Mu>{b.tagline} {co.code}</Mu></div></div>
          </div>
          <div className="text-end"><b>فاکتور فروش</b><div><Mu>شماره {i.number}</Mu></div><div><Mu>تاریخ {dt(i.issued_at)}</Mu></div></div>
        </header>
        <div className="my-4 grid gap-3 sm:grid-cols-2">
          <div className="rounded border border-slate-200 p-3"><Mu>خریدار</Mu><div><b>{c.name}</b></div>
            <Mu>کد {c.code}{c.customer_group ? ` · گروه ${c.customer_group}` : ''}{c.region ? ` · ${c.region}` : ''}</Mu><div><Mu>{c.address} {c.phone}</Mu></div></div>
          <div className="rounded border border-slate-200 p-3"><Mu>فروشنده / انبار</Mu><div><b>{q.data!.seller}</b></div><Mu>{q.data!.warehouse} · سفارش {q.data!.order_number}</Mu></div>
        </div>
        <table className="w-full text-sm">
          <thead><tr>{['ردیف', 'شرح کالا', 'تعداد', 'قیمت واحد', 'تخفیف', 'مبلغ'].map(h => <th key={h} className="border-b border-slate-300 p-2 text-start">{h}</th>)}</tr></thead>
          <tbody>{lines.map((l, n) => (
            <tr key={n}><td className="border-b p-2">{fa(n + 1)}</td><td className="border-b p-2">{l.description}</td><td className="border-b p-2">{fa(l.quantity)} {l.unit}</td>
              <td className="border-b p-2">{fa(l.unit_price)}</td><td className="border-b p-2">{fa(l.discount)}</td><td className="border-b p-2">{fa(l.line_total)}</td></tr>
          ))}</tbody>
        </table>
        <div className="mt-4 flex flex-wrap justify-between gap-4">
          <div>
            <span className="rounded px-2 py-0.5 text-sm text-white" style={{ background: color }}>{ST[i.status] ?? i.status}</span>
            <div className="mt-1"><Mu>پرداخت‌شده {fa(i.paid)}{returned > 0 ? ` · برگشتی ${fa(returned)}` : ''} · مانده {fa(Math.max(0, remaining))}{remaining < 0 ? ` (بستانکار ${fa(-remaining)})` : ''}</Mu></div>
            {pays.length > 0 && <div><Mu>پرداخت‌ها: {pays.map(p => `${fa(p.amount)} (${METHOD[p.method] ?? p.method})`).join('، ')}</Mu></div>}
          </div>
          <table className="min-w-[260px] text-sm"><tbody>
            <tr><td><Mu>جمع اقلام</Mu></td><td>{fa(i.subtotal ?? i.total)}</td></tr>
            {Number(i.tax) > 0 && <tr><td><Mu>مالیات ارزش افزوده</Mu></td><td>{fa(i.tax)}</td></tr>}
            {Number(i.shipping) > 0 && <tr><td><Mu>هزینه حمل</Mu></td><td>{fa(i.shipping)}</td></tr>}
            {returned > 0 && <tr><td><Mu>برگشت از فروش</Mu></td><td>-{fa(returned)}</td></tr>}
            <tr className="font-semibold"><td className="border-t border-slate-900 pt-2">مبلغ قابل پرداخت</td><td className="border-t border-slate-900 pt-2">{fa(Number(i.total) - returned)}</td></tr>
          </tbody></table>
        </div>
        {note && <section className="mt-4"><b>یادداشت</b><div className="whitespace-pre-wrap">{note}</div></section>}
        {terms && <section className="mt-4"><b>شرایط و توضیحات</b><div className="whitespace-pre-wrap">{terms}</div></section>}
        <div className="mt-10 flex justify-around text-sm text-slate-500"><span>امضای فروشنده</span><span>امضای خریدار</span></div>
      </main>
    </div>
  )
}
