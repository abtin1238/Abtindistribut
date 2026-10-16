import { send } from '../../lib/api'
import type { Resource } from '../../lib/types'
import { st, c, ref, T, N, D, S, O, patch } from './helpers'

export const automationResources: Resource[] = [
  { path: 'leads', title: 'سرنخ‌های فروش', endpoint: '/leads', columns: [c('title', 'عنوان'), ref('customer_id', 'مشتری', '/customers'), st('stage'), c('value', 'ارزش', 'money'), c('source', 'منبع'), c('next_followup', 'پیگیری بعدی', 'date')],
    create: { title: 'سرنخ جدید', fields: [T('title', 'عنوان', true), S('customer_id', 'مشتری', '/customers'), N('value', 'ارزش'), T('source', 'منبع'), D('next_followup', 'پیگیری بعدی'), { name: 'notes', label: 'یادداشت', type: 'textarea' }] },
    actions: [{ label: 'تغییر مرحله', fields: [O('stage', 'مرحله', [['new', 'جدید'], ['contacted', 'تماس‌گرفته'], ['qualified', 'واجد شرایط'], ['proposal', 'پیشنهاد'], ['negotiation', 'مذاکره'], ['won', 'موفق'], ['lost', 'ازدست‌رفته']], true), T('lost_reason', 'دلیل ازدست‌رفتن')], run: (r, v) => send(`/leads/${r.id}/stage`, v, 'PATCH') }] },
  { path: 'tasks', title: 'وظایف و پیگیری', endpoint: '/tasks', columns: [c('title', 'عنوان'), c('kind', 'نوع'), c('due_date', 'سررسید', 'date'), st(), ref('assignee_id', 'مسئول', '/users')],
    create: { title: 'وظیفهٔ جدید', fields: [T('title', 'عنوان', true), O('kind', 'نوع', [['task', 'وظیفه'], ['call', 'تماس']], true, 'task'), D('due_date', 'سررسید'), S('assignee_id', 'مسئول', '/users'), S('customer_id', 'مشتری', '/customers')] },
    actions: [{ label: 'انجام شد', when: r => r.status !== 'done', run: patch('/tasks/{id}', () => ({ status: 'done' })) }] },
  { path: 'proposals', title: 'پیشنهاد فروش', endpoint: '/proposals', newTo: '/proposals/new', columns: [c('number', 'شماره'), ref('customer_id', 'مشتری', '/customers'), st(), c('valid_until', 'اعتبار تا', 'date'), c('total', 'جمع', 'money')],
    actions: [{ label: 'ارسال', when: r => r.status === 'draft', run: r => send(`/proposals/${r.id}/send`) }, { label: 'پذیرش (ساخت سفارش)', when: r => r.status === 'sent', fields: [S('warehouse_id', 'انبار', '/warehouses', true)], run: (r, v) => send(`/proposals/${r.id}/accept`, v) }, { label: 'رد', danger: true, when: r => r.status === 'sent', run: r => send(`/proposals/${r.id}/reject`) }] },
  { path: 'targets', title: 'اهداف فروش', endpoint: '/targets', columns: [ref('user_id', 'کاربر', '/users'), c('period', 'دوره'), c('sales_target', 'هدف', 'money'), c('commission_percent', 'درصد پورسانت', 'num')],
    create: { title: 'هدف جدید', fields: [S('user_id', 'کاربر', '/users', true), { name: 'period', label: 'دوره (YYYY-MM)', required: true, placeholder: '2026-10' }, N('sales_target', 'هدف فروش', true), N('commission_percent', 'درصد پورسانت')] } },
]
