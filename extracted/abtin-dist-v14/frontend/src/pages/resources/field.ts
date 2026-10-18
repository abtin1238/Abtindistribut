import { send } from '../../lib/api'
import type { Resource } from '../../lib/types'
import { st, c, ref, D, S, M, T, N, O } from './helpers'

export const fieldResources: Resource[] = [
  { path: 'visits', title: 'ویزیت‌ها', endpoint: '/visits', columns: [ref('customer_id', 'مشتری', '/customers'), ref('user_id', 'ویزیتور', '/users'), c('started_at', 'شروع', 'date'), c('ended_at', 'پایان', 'date'), c('result', 'نتیجه'), c('gps_status', 'GPS'), c('distance_m', 'فاصله (متر)', 'num')] },
  { path: 'visit-plans', title: 'برنامهٔ ویزیت', endpoint: '/visit-plans', columns: [c('id', 'شماره', 'num'), ref('user_id', 'ویزیتور', '/users'), c('day', 'روز', 'date'), st()],
    create: { title: 'برنامهٔ جدید', fields: [S('user_id', 'ویزیتور', '/users', true), D('day', 'روز', true), M('customer_ids', 'مشتریان', '/customers')] } },
  { path: 'geofences', title: 'ناحیه‌های جغرافیایی', endpoint: '/geofences', perm: 'gps.read', columns: [c('name', 'نام'), c('kind', 'نوع'), c('lat', 'عرض'), c('lng', 'طول'), c('radius_m', 'شعاع (متر)', 'num')],
    create: { title: 'ناحیهٔ جدید', fields: [T('name', 'نام', true), O('kind', 'نوع', [['area', 'منطقه'], ['depot', 'انبار'], ['customer', 'مشتری'], ['restricted', 'ممنوعه']], true, 'area'), N('lat', 'عرض جغرافیایی', true), N('lng', 'طول جغرافیایی', true), N('radius_m', 'شعاع (متر)', true, 100)] },
    actions: [{ label: 'حذف', danger: true, confirm: 'ناحیه غیرفعال شود؟', run: r => send(`/geofences/${r.id}`, undefined, 'DELETE') }] },
  { path: 'geofence-events', title: 'رویدادهای ناحیه', endpoint: '/geofences/events', perm: 'gps.read', columns: [c('user', 'کاربر'), c('geofence', 'ناحیه'), c('kind', 'رویداد'), c('at', 'زمان', 'date')] },
]
