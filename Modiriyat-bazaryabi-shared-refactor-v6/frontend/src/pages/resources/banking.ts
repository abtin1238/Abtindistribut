import type { Resource } from '../../lib/types'
import { st, c, ref, T, N, S, patch, toggle } from './helpers'

export const bankingResources: Resource[] = [
  { path: 'bank-accounts', title: 'حساب‌های بانکی', endpoint: '/bank-accounts', columns: [c('name', 'نام'), c('bank_name', 'بانک'), c('account_number', 'شماره حساب'), c('iban', 'شبا'), c('balance', 'مانده', 'money'), c('active', 'فعال', 'bool')],
    create: { title: 'حساب جدید', fields: [T('name', 'نام', true), T('bank_name', 'بانک'), T('branch', 'شعبه'), T('account_number', 'شماره حساب'), T('iban', 'شبا'), T('holder', 'صاحب حساب'), N('opening_balance', 'مانده اول دوره')] }, actions: [toggle('/bank-accounts/{id}')] },
  { path: 'chequebooks', title: 'دسته‌چک', endpoint: '/chequebooks', columns: [ref('bank_account_id', 'حساب', '/bank-accounts'), c('series', 'سری'), c('start_no', 'از', 'num'), c('end_no', 'تا', 'num'), st()],
    create: { title: 'دسته‌چک جدید', fields: [S('bank_account_id', 'حساب بانکی', '/bank-accounts', true), T('series', 'سری'), N('start_no', 'از شماره', true), N('end_no', 'تا شماره', true)] },
    actions: [{ label: 'لغو', danger: true, confirm: 'دسته‌چک لغو شود؟', run: patch('/chequebooks/{id}', () => ({ status: 'cancelled' })) }] },
]
