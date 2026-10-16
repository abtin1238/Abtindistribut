import type { Resource } from '../../lib/types'
import { c, ref, T, S, M, toggle } from './helpers'

export const authOrgResources: Resource[] = [
  { path: 'users', title: 'کاربران', endpoint: '/users', perm: 'admin.read', columns: [c('name', 'نام'), c('username', 'نام کاربری'), ref('role_id', 'نقش', '/roles'), c('active', 'فعال', 'bool')],
    create: { title: 'کاربر جدید', fields: [T('name', 'نام', true), T('username', 'نام کاربری', true), { name: 'password', label: 'رمز عبور', type: 'password', required: true }, S('role_id', 'نقش', '/roles', true)], build: (v, x) => ({ ...v, company_ids: [x.companyId] }) },
    actions: [toggle('/users/{id}')] },
  { path: 'roles', title: 'نقش‌ها', endpoint: '/roles', perm: 'admin.read', columns: [c('name', 'نام'), { key: 'permissions', label: 'تعداد مجوز', render: r => String((r.permissions ?? []).length) }],
    create: { title: 'نقش جدید', fields: [T('name', 'نام', true), M('permissions', 'مجوزها', '/permissions')] } },
  { path: 'audit', title: 'گزارش فعالیت‌ها', endpoint: '/audit', perm: 'admin.read', columns: [c('created_at', 'زمان', 'date'), ref('user_id', 'کاربر', '/users'), c('action', 'عملیات'), c('entity', 'موجودیت'), c('entity_id', 'شناسه', 'num')] },
]
