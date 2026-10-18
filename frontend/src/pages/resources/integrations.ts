import { send } from '../../lib/api'
import type { Resource } from '../../lib/types'
import { c, T, N, S, M, del } from './helpers'

export const integrationsResources: Resource[] = [
  { path: 'api-keys', title: 'کلیدهای API', endpoint: '/api-keys', columns: [c('name', 'نام'), c('prefix', 'پیشوند'), c('last_used_at', 'آخرین استفاده', 'date'), c('expires_at', 'انقضا', 'date')],
    create: { title: 'کلید جدید', fields: [T('name', 'نام', true), S('role_id', 'نقش', '/roles', true), N('expires_in_days', 'انقضا (روز)')] }, actions: [del('/api-keys/{id}')] },
  { path: 'webhooks', title: 'وبهوک‌ها', endpoint: '/webhooks', columns: [c('url', 'نشانی'), c('active', 'فعال', 'bool')],
    create: { title: 'وبهوک جدید', fields: [T('url', 'نشانی (https)', true), M('events', 'رویدادها', '/webhooks/events')] },
    actions: [{ label: 'آزمایش', run: r => send(`/webhooks/${r.id}/test`) }, del('/webhooks/{id}')] },
]
