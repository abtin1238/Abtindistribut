import DocForm from '../components/DocForm'
import { send } from '../lib/api'
import type { Field } from '../lib/types'
const sel = (name: string, label: string, from: string, required = true): Field => ({ name, label, type: 'select', optionsFrom: { endpoint: from }, required })
const num = (name: string, label: string, required = true, def?: number): Field => ({ name, label, type: 'number', required, def })
export function OrderNew() {
  return <DocForm title="سفارش جدید" endpoint="/orders" back="/orders"
    header={[sel('customer_id', 'مشتری', '/customers'), sel('warehouse_id', 'انبار', '/warehouses'), num('shipping', 'هزینهٔ حمل', false, 0), { name: 'note', label: 'یادداشت فاکتور', type: 'textarea' }]}
    line={[sel('product_id', 'کالا', '/products'), num('quantity', 'تعداد', true, 1), num('discount', 'تخفیف', false, 0)]}
    build={(h, items) => ({ ...h, items })}
    then={{ label: 'ثبت و صدور فاکتور', run: (o: { id: number }) => send(`/orders/${o.id}/approve`) }} />
}
export function PurchaseNew() {
  return <DocForm title="خرید جدید" endpoint="/purchases" back="/purchases"
    header={[sel('supplier_id', 'تأمین‌کننده', '/suppliers'), sel('warehouse_id', 'انبار', '/warehouses'), num('freight', 'هزینهٔ جانبی', false, 0)]}
    line={[sel('product_id', 'کالا', '/products'), num('quantity', 'تعداد', true, 1), num('unit_cost', 'بهای واحد', true), num('discount', 'تخفیف', false, 0)]}
    build={(h, items) => ({ ...h, items })} />
}
export function TransferNew() {
  return <DocForm title="انتقال جدید بین انبارها" endpoint="/stock/transfers" back="/transfers"
    header={[sel('from_warehouse_id', 'از انبار', '/warehouses'), sel('to_warehouse_id', 'به انبار', '/warehouses'), { name: 'note', label: 'یادداشت' }]}
    line={[sel('product_id', 'کالا', '/products'), num('quantity', 'تعداد', true, 1)]}
    build={(h, items) => ({ ...h, items })} />
}
export function ProposalNew() {
  return <DocForm title="پیشنهاد فروش جدید" endpoint="/proposals" back="/proposals"
    header={[sel('customer_id', 'مشتری', '/customers'), { name: 'valid_until', label: 'اعتبار تا', type: 'date' }, { name: 'notes', label: 'یادداشت', type: 'textarea' }]}
    line={[sel('product_id', 'کالا', '/products'), num('quantity', 'تعداد', true, 1)]}
    build={(h, items) => ({ ...h, items })} />
}
export function JournalNew() {
  return <DocForm title="سند حسابداری جدید" endpoint="/journal" back="/journal"
    header={[{ name: 'description', label: 'شرح سند', required: true }]}
    line={[{ name: 'account_code', label: 'کد حساب', required: true }, num('debit', 'بدهکار', false, 0), num('credit', 'بستانکار', false, 0), { name: 'memo', label: 'شرح' }]}
    build={(h, lines) => ({ ...h, lines })} />
}
