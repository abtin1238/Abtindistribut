import { useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, get, send } from '../../lib/api'
import { Btn, Card, ErrorBox } from '../ui'
import { FormSection } from './FormSection'

type Brand = { name?: string; tagline?: string; color?: string; has_logo?: boolean; logo_url?: string | null }
/** هویت برند: نام، شعار، رنگ و لوگو (PNG/JPG/WebP تا ۱ مگابایت) */
export default function BrandSettings() {
  const qc = useQueryClient(), file = useRef<HTMLInputElement>(null)
  const q = useQuery({ queryKey: ['brand'], queryFn: () => get<Brand>('/settings/brand'), retry: false })
  const [err, setErr] = useState<unknown>(null)
  const refresh = () => { qc.invalidateQueries({ queryKey: ['brand'] }); qc.invalidateQueries({ queryKey: ['set', '/settings/brand'] }) }
  async function upload(f?: File) {
    if (!f) return
    setErr(null)
    try { const form = new FormData(); form.append('file', f); await api('/settings/logo', { method: 'POST', form }); refresh() } catch (x) { setErr(x) }
  }
  async function remove() {
    if (!confirm('لوگو حذف شود؟')) return
    setErr(null)
    try { await send('/settings/logo', undefined, 'DELETE'); refresh() } catch (x) { setErr(x) }
  }
  return (
    <>
      <Card title="لوگو">
        <div className="flex flex-wrap items-center gap-4">
          <div className="lgprev">{q.data?.logo_url ? <img src={q.data.logo_url} alt="لوگوی شرکت" /> : <small className="text-mut">بدون لوگو</small>}</div>
          <div className="flex flex-col gap-2">
            <input ref={file} type="file" hidden accept="image/png,image/jpeg,image/webp" onChange={e => { upload(e.target.files?.[0]); e.target.value = '' }} />
            <div className="flex gap-2">
              <Btn variant="ghost" onClick={() => file.current?.click()}>انتخاب لوگو</Btn>
              <Btn variant="ghost" disabled={!q.data?.has_logo} onClick={remove}>حذف لوگو</Btn>
            </div>
            <small className="text-mut">PNG / JPG / WebP، حداکثر ۱ مگابایت</small>
          </div>
        </div>
        {err != null && <ErrorBox error={err} />}
      </Card>
      <FormSection title="هویت برند" path="/settings/brand" extra={() => qc.invalidateQueries({ queryKey: ['brand'] })}
        fields={[{ name: 'name', label: 'نام' }, { name: 'tagline', label: 'شعار' }, { name: 'color', label: 'رنگ برند', type: 'color' }]} />
    </>
  )
}
