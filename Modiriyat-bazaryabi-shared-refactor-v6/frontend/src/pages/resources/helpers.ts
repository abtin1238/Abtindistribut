import { createElement } from 'react'
import { send } from '../../lib/api'
import { BranchName } from '../../components/BranchName'
import type { Action, Col, Field, Row } from '../../lib/types'

export const STATUS: Record<string, string> = {
  draft: 'پیش‌نویس', open: 'باز', partial: 'پرداخت جزئی', paid: 'پرداخت‌شده', cancelled: 'لغو‌شده', approved: 'تأییدشده', reserved: 'رزروشده',
  delivered: 'تحویل‌شده', pending: 'در انتظار', received: 'دریافت‌شده', in_transit: 'در راه', returned: 'برگشتی', deposited: 'در جریان وصول',
  cleared: 'وصول‌شده', bounced: 'برگشت‌خورده', endorsed: 'خرج‌شده', posted: 'قطعی', reversed: 'معکوس‌شده', approved_leave: 'تأییدشده',
  rejected: 'ردشده', failed: 'ناموفق', assigned: 'تخصیص‌یافته', done: 'انجام‌شده', new: 'جدید', won: 'موفق', lost: 'ازدست‌رفته', sent: 'ارسال‌شده',
  accepted: 'پذیرفته‌شده', active: 'فعال', closed: 'بسته',
}
export const st = (key = 'status'): Col => ({ key, label: 'وضعیت', render: (r: Row) => STATUS[r[key]] ?? String(r[key] ?? '—') })
export const c = (key: string, label: string, kind?: Col['kind']): Col => ({ key, label, kind })
export const ref = (key: string, label: string, to: string): Col => ({ key, label, kind: 'ref', ref: to })
export const T = (name: string, label: string, required = false): Field => ({ name, label, required })
export const N = (name: string, label: string, required = false, def?: number): Field => ({ name, label, type: 'number', required, def })
export const D = (name: string, label: string, required = false): Field => ({ name, label, type: 'date', required })
export const S = (name: string, label: string, from: string, required = false): Field => ({ name, label, type: 'select', optionsFrom: { endpoint: from }, required })
export const O = (name: string, label: string, options: [string, string][], required = false, def?: string): Field => ({ name, label, type: 'select', options: options.map(([value, label]) => ({ value, label })), required, def })
export const M = (name: string, label: string, from: string): Field => ({ name, label, type: 'multi', optionsFrom: { endpoint: from } })
export const BR = (name = 'branch_id', label = 'شعبه'): Field => ({ name, label, type: 'select', optionsFrom: { endpoint: '/organizations', pick: 'branches', companyScoped: true } })
export const branchCol = (key = 'branch_id', label = 'شعبه'): Col => ({ key, label, render: (r: Row) => createElement(BranchName, { id: r[key] }) })
export const patch = (path: string, body: (r: Row) => unknown) => (r: Row) => send(path.replace('{id}', String(r.id)), body(r), 'PATCH')
export const toggle = (path: string, field = 'active'): Action => ({ label: 'فعال/غیرفعال', run: patch(path, r => ({ [field]: !r[field] })) })
export const del = (path: string): Action => ({ label: 'حذف', danger: true, confirm: 'این مورد حذف شود؟', run: r => send(path.replace('{id}', String(r.id)), undefined, 'DELETE') })
export const retItems = (fields: Field[] = [S('product_id', 'کالا', '/products', true), N('quantity', 'تعداد', true)]) => fields.concat([T('reason', 'دلیل')])
