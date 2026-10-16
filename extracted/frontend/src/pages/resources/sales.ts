import { send } from '../../lib/api'
import type { Resource } from '../../lib/types'
import { st, c, ref, S, retItems } from './helpers'

export const salesResources: Resource[] = [
  { path: 'orders', title: 'سفارش‌ها', endpoint: '/orders', paged: true, newTo: '/orders/new', perm: 'sales.read',
    columns: [c('number', 'شماره'), ref('customer_id', 'مشتری', '/customers'), ref('warehouse_id', 'انبار', '/warehouses'), st(), c('total', 'جمع', 'money'), c('shipping', 'حمل', 'money'), c('created_at', 'تاریخ', 'date')],
    actions: [{ label: 'تأیید و صدور فاکتور', when: r => r.status === 'draft' || r.status === 'pending', run: r => send(`/orders/${r.id}/approve`) },
      { label: 'تخصیص مأمور', fields: [S('driver_id', 'مأمور پخش', '/users', true)], run: (r, v) => send(`/orders/${r.id}/assign-delivery`, v) },
      { label: 'برگشت از فروش', fields: retItems(), run: (r, v) => send(`/orders/${r.id}/return`, { items: [{ product_id: v.product_id, quantity: v.quantity }], reason: v.reason ?? '' }) },
      { label: 'لغو', danger: true, when: r => r.status !== 'cancelled' && r.status !== 'delivered', confirm: 'سفارش لغو و رزرو آزاد شود؟', run: r => send(`/orders/${r.id}/cancel`) }] },
  { path: 'invoices', title: 'فاکتورها', endpoint: '/invoices', perm: 'sales.read',
    columns: [c('number', 'شماره'), c('customer_name', 'مشتری'), c('order_number', 'سفارش'), c('total', 'جمع', 'money'), c('paid', 'پرداخت‌شده', 'money'), c('remaining', 'مانده', 'money'), st(), c('issued_at', 'تاریخ', 'date')],
    actions: [{ label: 'چاپ', run: async r => { window.open(`/web/invoice.html?id=${r.id}`, '_blank', 'noopener') } }] },
]
