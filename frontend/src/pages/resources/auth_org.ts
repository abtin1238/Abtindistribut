import type { Resource } from '../../lib/types'
import { send } from '../../lib/api'
import { auditAct, auditEnt, auditTime } from '../../lib/auditLabels'
import { c, ref, T, S, M, toggle, BR, branchCol } from './helpers'

export const authOrgResources: Resource[] = [
  { path: 'users', title: 'کاربران', endpoint: '/users', perm: 'admin.read', columns: [c('name', 'نام'), c('username', 'نام کاربری'), ref('role_id', 'نقش', '/roles'), branchCol(), c('active', 'فعال', 'bool')],
    create: { title: 'کاربر جدید', fields: [T('name', 'نام', true), T('username', 'نام کاربری', true), { name: 'password', label: 'رمز عبور', type: 'password', required: true }, S('role_id', 'نقش', '/roles', true), BR()], build: (v, x) => ({ ...v, company_ids: [x.companyId] }) },
    actions: [toggle('/users/{id}'),
      { label: 'تغییر نقش/شعبه', fields: [S('role_id', 'نقش', '/roles', true), BR()], prefill: r => ({ role_id: r.role_id, branch_id: r.branch_id }), run: (r, v) => send(`/users/${r.id}`, v, 'PATCH') }] },
  { path: 'roles', title: 'نقش‌ها', endpoint: '/roles', perm: 'admin.read', columns: [c('name', 'نام'), { key: 'permissions', label: 'تعداد مجوز', render: r => String((r.permissions ?? []).length) }],
    create: { title: 'نقش جدید', fields: [T('name', 'نام', true), M('permissions', 'مجوزها', '/permissions')] } },
  { path: 'audit', title: 'گزارش فعالیت‌ها', endpoint: '/audit', perm: 'admin.read', columns: [{ key: 'created_at', label: 'زمان', render: r => auditTime(r.created_at) }, { key: 'user_name', label: 'کاربر', render: r => r.user_name || (r.user_id ? `#${r.user_id}` : '—') },
      { key: 'action', label: 'عملیات', render: r => auditAct(r.action) }, { key: 'entity', label: 'موجودیت', render: r => auditEnt(r.entity) }, c('entity_id', 'شناسه', 'num')] },
]
