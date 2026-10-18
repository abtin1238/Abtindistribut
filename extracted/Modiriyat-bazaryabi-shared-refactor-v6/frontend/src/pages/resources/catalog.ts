import { send } from '../../lib/api'
import type { Resource } from '../../lib/types'
import { c, ref, T, N, S, toggle, del } from './helpers'

export const catalogResources: Resource[] = [
  { path: 'products', title: 'کالا و قیمت', endpoint: '/products', perm: 'catalog.read',
    columns: [c('sku', 'کد کالا'), c('name', 'نام'), c('unit', 'واحد'), c('base_price', 'قیمت پایه', 'money'), c('avg_cost', 'بهای میانگین', 'money'), c('min_stock', 'حداقل موجودی', 'num'), ref('brand_id', 'برند', '/brands'), ref('category_id', 'دسته', '/categories'), c('active', 'فعال', 'bool')],
    create: { title: 'کالای جدید', fields: [T('sku', 'کد کالا', true), T('name', 'نام', true), T('unit', 'واحد'), N('base_price', 'قیمت پایه'), N('min_stock', 'حداقل موجودی'), S('brand_id', 'برند', '/brands'), S('category_id', 'دسته', '/categories')] },
    actions: [toggle('/products/{id}'), { label: 'ویرایش قیمت', fields: [N('base_price', 'قیمت پایه', true)], run: (r, v) => send(`/products/${r.id}`, v, 'PATCH') }] },
  { path: 'brands', title: 'برندها', endpoint: '/brands', columns: [c('name', 'نام')], create: { title: 'برند جدید', fields: [T('name', 'نام', true)] }, actions: [del('/brands/{id}')] },
  { path: 'categories', title: 'دسته‌بندی کالا', endpoint: '/categories', columns: [c('name', 'نام'), ref('parent_id', 'والد', '/categories')],
    create: { title: 'دستهٔ جدید', fields: [T('name', 'نام', true), S('parent_id', 'والد', '/categories')] }, actions: [del('/categories/{id}')] },
  { path: 'price-rules', title: 'قیمت‌گذاری', endpoint: '/price-rules',
    columns: [ref('product_id', 'کالا', '/products'), c('customer_group', 'گروه'), c('price', 'قیمت', 'money'), c('discount_percent', 'درصد تخفیف', 'num'), c('min_qty', 'حداقل تعداد', 'num'), c('starts_at', 'از', 'date'), c('ends_at', 'تا', 'date'), c('active', 'فعال', 'bool')],
    create: { title: 'قانون جدید', fields: [S('product_id', 'کالا', '/products', true), T('customer_group', 'گروه مشتری'), N('price', 'قیمت ثابت'), N('discount_percent', 'درصد تخفیف'), N('min_qty', 'حداقل تعداد', false, 1), { name: 'starts_at', label: 'شروع', type: 'date' }, { name: 'ends_at', label: 'پایان', type: 'date' }] },
    actions: [toggle('/price-rules/{id}'), del('/price-rules/{id}')] },
]
