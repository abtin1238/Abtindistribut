import type { Resource } from '../../lib/types'
import { st, c, ref, T, N, D, S } from './helpers'

export const contractsResources: Resource[] = [
  { path: 'contracts', title: 'قراردادها', endpoint: '/contracts', columns: [c('number', 'شماره'), c('title', 'عنوان'), ref('customer_id', 'مشتری', '/customers'), ref('supplier_id', 'تأمین‌کننده', '/suppliers'), c('start_date', 'شروع', 'date'), c('end_date', 'پایان', 'date'), c('amount', 'مبلغ', 'money'), st()],
    create: { title: 'قرارداد جدید', fields: [T('title', 'عنوان', true), S('customer_id', 'مشتری', '/customers'), S('supplier_id', 'تأمین‌کننده', '/suppliers'), D('start_date', 'شروع'), D('end_date', 'پایان'), N('amount', 'مبلغ'), T('note', 'یادداشت')] } },
]
