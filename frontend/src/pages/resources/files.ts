import type { Resource } from '../../lib/types'
import { c, del } from './helpers'

export const filesResources: Resource[] = [
  { path: 'documents', title: 'اسناد و پیوست‌ها', endpoint: '/documents', columns: [c('filename', 'فایل'), c('entity', 'مربوط به'), c('entity_id', 'شناسه', 'num'), c('size', 'حجم', 'num'), c('created_at', 'تاریخ', 'date')],
    actions: [{ label: 'دانلود', run: async r => { const { download } = await import('../../lib/api'); await download(`/documents/${r.id}/download`, String(r.filename)) } }, del('/documents/{id}')] },
]
