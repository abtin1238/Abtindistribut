import { send } from '../../lib/api'
import type { Resource } from '../../lib/types'
import { st, c, ref, T, N, D, S, O, del } from './helpers'

export const hrResources: Resource[] = [
  { path: 'employees', title: 'کارکنان', endpoint: '/employees', columns: [c('name', 'نام'), c('position', 'سمت'), c('phone', 'تلفن'), c('salary', 'حقوق', 'money'), c('active', 'فعال', 'bool')],
    actions: [{ label: 'تخصیص شیفت', fields: [S('shift_id', 'شیفت', '/shifts', true)], run: (r, v) => send(`/employees/${r.id}/shift`, { shift_id: v.shift_id }, 'PUT') }],
    create: { title: 'کارمند جدید', fields: [T('name', 'نام', true), T('position', 'سمت'), T('phone', 'تلفن'), N('salary', 'حقوق پایه')] } },
  { path: 'attendance', title: 'حضور و غیاب', endpoint: '/attendance', columns: [c('user_id', 'کاربر'), c('employee_id', 'کارمند'), c('check_in', 'ورود', 'date'), c('check_out', 'خروج', 'date')],
    create: { title: 'ثبت ورود', endpoint: '/attendance/check-in', fields: [] }, top: [{ label: 'ثبت خروج', run: () => send('/attendance/check-out') }] },
  { path: 'leaves', title: 'مرخصی', endpoint: '/leaves', columns: [ref('employee_id', 'کارمند', '/employees'), c('kind', 'نوع'), c('start_date', 'از', 'date'), c('end_date', 'تا', 'date'), st(), c('reason', 'دلیل')],
    create: { title: 'درخواست مرخصی', fields: [S('employee_id', 'کارمند', '/employees', true), O('kind', 'نوع', [['annual', 'استحقاقی'], ['sick', 'استعلاجی'], ['unpaid', 'بدون حقوق']], true, 'annual'), D('start_date', 'از', true), D('end_date', 'تا', true), T('reason', 'دلیل')] },
    actions: [{ label: 'تأیید', when: r => r.status === 'pending', run: r => send(`/leaves/${r.id}/approve`) }, { label: 'رد', danger: true, when: r => r.status === 'pending', run: r => send(`/leaves/${r.id}/reject`) }] },
  { path: 'payroll', title: 'حقوق و دستمزد', endpoint: '/payroll/runs', columns: [c('period', 'دوره'), st(), c('total_base', 'پایه', 'money'), c('total_bonus', 'مزایا', 'money'), c('total_deduction', 'کسورات', 'money'), c('total_net', 'خالص', 'money')],
    create: { title: 'لیست حقوق جدید', fields: [{ name: 'period', label: 'دوره (YYYY-MM)', required: true, placeholder: '2026-10' }] },
    actions: [{ label: 'ثبت سند', when: r => r.status === 'draft', run: r => send(`/payroll/runs/${r.id}/post`) }, { label: 'پرداخت', when: r => r.status === 'posted', run: r => send(`/payroll/runs/${r.id}/pay`) }, { ...del('/payroll/runs/{id}'), when: r => r.status === 'draft' }] },
  { path: 'shifts', title: 'شیفت‌ها', endpoint: '/shifts', columns: [c('name', 'نام'), c('start_time', 'شروع'), c('end_time', 'پایان'), c('grace_minutes', 'مهلت (دقیقه)', 'num'), c('active', 'فعال', 'bool')],
    create: { title: 'شیفت جدید', fields: [T('name', 'نام', true), { ...T('start_time', 'شروع (HH:MM)', true), placeholder: '08:00' }, { ...T('end_time', 'پایان (HH:MM)', true), placeholder: '17:00' }, N('grace_minutes', 'مهلت تأخیر (دقیقه)', false, 0)] },
    actions: [{ label: 'غیرفعال', danger: true, when: r => !!r.active, confirm: 'شیفت غیرفعال شود؟', run: r => send(`/shifts/${r.id}`, { active: false }, 'PATCH') }] },
]
