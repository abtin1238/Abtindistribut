import { send } from '../../lib/api'
import type { Resource } from '../../lib/types'
import { st, c, ref, S, T, N, O, retItems } from './helpers'

export const purchasingResources: Resource[] = [
  { path: 'suppliers', title: 'تأمین‌کنندگان', endpoint: '/suppliers', columns: [c('name', 'نام'), c('phone', 'تلفن'), c('balance', 'مانده', 'money')], create: { title: 'تأمین‌کنندهٔ جدید', fields: [T('name', 'نام', true), T('phone', 'تلفن')] } },
  { path: 'purchases', title: 'خرید', endpoint: '/purchases', newTo: '/purchases/new', columns: [c('number', 'شماره'), ref('supplier_id', 'تأمین‌کننده', '/suppliers'), ref('warehouse_id', 'انبار', '/warehouses'), st(), c('total', 'جمع', 'money'), c('freight', 'هزینهٔ جانبی', 'money'), c('created_at', 'تاریخ', 'date')],
    actions: [{ label: 'دریافت کالا', when: r => r.status === 'draft' || r.status === 'partial', run: r => send(`/purchases/${r.id}/receive`) },
      { label: 'رسید جزئی', when: r => r.status === 'draft' || r.status === 'partial', fields: [S('product_id', 'کالا', '/products', true), N('quantity', 'تعداد', true)], run: (r, v) => send(`/purchases/${r.id}/receive`, { items: [{ product_id: v.product_id, quantity: v.quantity }] }) },
      { label: 'تسهیم هزینه', when: r => r.status === 'draft', fields: [T('label', 'عنوان (گمرک/حمل…)', true), N('amount', 'مبلغ', true), O('basis', 'مبنا', [['value', 'ارزش'], ['qty', 'تعداد']], true, 'value')], run: (r, v) => send(`/purchases/${r.id}/allocate-cost`, v) },
      { label: 'لغو', danger: true, when: r => r.status === 'draft', confirm: 'سفارش خرید لغو شود؟', run: r => send(`/purchases/${r.id}/cancel`) },
      { label: 'برگشت', when: r => r.status === 'received' || r.status === 'partial', fields: retItems(), run: (r, v) => send(`/purchases/${r.id}/return`, { items: [{ product_id: v.product_id, quantity: v.quantity }], reason: v.reason ?? '' }) }] },
]
