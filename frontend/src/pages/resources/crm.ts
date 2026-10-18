import type { Resource } from '../../lib/types'
import { send } from '../../lib/api'
import { c, T, N, O, BR, branchCol } from './helpers'

export const crmResources: Resource[] = [
  { path: 'customers', title: 'مشتریان', endpoint: '/customers', paged: true, perm: 'crm.read',
    columns: [c('code', 'کد'), c('name', 'نام'), c('phone', 'تلفن'), c('region', 'منطقه'), c('customer_group', 'گروه'), c('credit_limit', 'سقف اعتبار', 'money'), branchCol(), c('balance', 'مانده', 'money')],
    create: { title: 'مشتری جدید', fields: [T('code', 'کد', true), T('name', 'نام', true), T('phone', 'تلفن'), T('address', 'نشانی'), T('region', 'منطقه'), T('customer_group', 'گروه'), N('credit_limit', 'سقف اعتبار'), BR()] },
    actions: [
      { label: 'ویرایش', fields: [T('name', 'نام', true), T('phone', 'تلفن'), T('region', 'منطقه'), T('customer_group', 'گروه'), N('credit_limit', 'سقف اعتبار'), BR()],
        prefill: r => ({ name: r.name, phone: r.phone, region: r.region, customer_group: r.customer_group, credit_limit: r.credit_limit, branch_id: r.branch_id }),
        run: (r, v) => send(`/customers/${r.id}`, v, 'PATCH') },
      { label: 'آدرس جدید', fields: [T('title', 'عنوان', true), O('kind', 'نوع', [['delivery', 'تحویل'], ['billing', 'صورت‌حساب'], ['other', 'سایر']], true, 'delivery'), T('address', 'نشانی'), T('region', 'منطقه'), N('lat', 'عرض جغرافیایی'), N('lng', 'طول جغرافیایی')], run: (r, v) => send(`/customers/${r.id}/addresses`, v) },
      { label: 'مخاطب جدید', fields: [T('name', 'نام', true), T('role', 'سمت'), T('phone', 'تلفن'), T('email', 'ایمیل')], run: (r, v) => send(`/customers/${r.id}/contacts`, v) },
    ] },
]
