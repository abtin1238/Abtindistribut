import { createElement } from 'react'
import { Link } from 'react-router-dom'
import { send } from '../../lib/api'
import type { Resource } from '../../lib/types'
import { st, c, ref, T, N, S, O, D } from './helpers'

export const inventoryResources: Resource[] = [
  { path: 'warehouses', title: 'انبارها', endpoint: '/warehouses', columns: [c('name', 'نام'), c('address', 'نشانی'), c('active', 'فعال', 'bool')],
    create: { title: 'انبار جدید', fields: [T('name', 'نام', true), T('address', 'نشانی')], build: (v, x) => ({ ...v, company_id: x.companyId }) } },
  { path: 'stock', title: 'انبار', endpoint: '/stock', perm: 'inventory.read', columns: [c('product', 'کالا'), c('sku', 'کد'), c('warehouse', 'انبار'), c('quantity', 'موجودی', 'num'), c('reserved', 'رزرو', 'num'), c('location', 'قفسه')],
    create: { title: 'ثبت موجودی', endpoint: '/stock/adjust', fields: [S('warehouse_id', 'انبار', '/warehouses', true), S('product_id', 'کالا', '/products', true), O('kind', 'نوع', [['in', 'ورود به انبار'], ['out', 'خروج از انبار']], true, 'in'), N('quantity', 'تعداد', true), T('reference', 'توضیح / مرجع'), T('reason', 'دلیل (برای خروج الزامی)'), T('batch_no', 'شماره بچ'), D('expiry_date', 'تاریخ انقضا')] } },
  { path: 'transfers', title: 'انتقال بین انبارها', endpoint: '/stock/transfers', newTo: '/transfers/new', columns: [c('number', 'شماره'), ref('from_warehouse_id', 'از', '/warehouses'), ref('to_warehouse_id', 'به', '/warehouses'), c('products', 'اقلام'), c('items_count', 'تعداد قلم', 'num'), st()],
    actions: [{ label: 'دریافت', when: r => r.status === 'in_transit', run: r => send(`/stock/transfers/${r.id}/receive`) }, { label: 'لغو', danger: true, when: r => r.status === 'in_transit', confirm: 'انتقال لغو شود؟', run: r => send(`/stock/transfers/${r.id}/cancel`) }] },
  { path: 'stock-moves', title: 'گردش انبار', endpoint: '/stock/moves', perm: 'inventory.read', columns: [c('created_at', 'زمان', 'date'), c('product', 'کالا'), c('warehouse', 'انبار'), c('kind', 'نوع'), c('quantity', 'تعداد', 'num'), c('reason', 'دلیل'), c('reference', 'مرجع'), c('user', 'کاربر')] },
  { path: 'stock-batches', title: 'بچ و انقضا', endpoint: '/stock/batches', perm: 'inventory.read', columns: [c('product', 'کالا'), c('warehouse', 'انبار'), c('batch_no', 'بچ'), c('expiry_date', 'انقضا', 'date'), c('days_to_expiry', 'روز تا انقضا', 'num'), c('quantity', 'موجودی', 'num'), c('status', 'وضعیت')] },
  { path: 'stock-counts', title: 'انبارگردانی', endpoint: '/stock/counts', perm: 'inventory.read', columns: [{ key: 'number', label: 'شماره', render: r => createElement(Link, { to: `/stock-counts/${r.id}`, className: 'text-blue-600 underline' }, r.number) }, ref('warehouse_id', 'انبار', '/warehouses'), st(), c('note', 'توضیح'), c('created_at', 'تاریخ', 'date')],
    create: { title: 'برگه‌ی انبارگردانی جدید', fields: [S('warehouse_id', 'انبار', '/warehouses', true), T('note', 'توضیح')] },
    actions: [{ label: 'شمارش', when: r => r.status === 'draft' || r.status === 'counting', confirm: 'به صفحه‌ی شمارش بروید؟', run: async r => { window.location.assign(`/app/stock-counts/${r.id}`) } }, { label: 'لغو', danger: true, when: r => r.status === 'draft' || r.status === 'counting', confirm: 'برگه لغو شود؟', run: r => send(`/stock/counts/${r.id}/cancel`) }] },
]
