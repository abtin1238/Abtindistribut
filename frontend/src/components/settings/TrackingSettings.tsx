import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { get, send } from '../../lib/api'
import { Btn, Card, ErrorBox } from '../ui'

type Cfg = { enabled: boolean; work_start: string; work_end: string; work_days: number[]; interval_s: number; min_distance_m: number; retention_days: number; tz_offset_min: number }
const DAYS: [number, string][] = [[5, 'شنبه'], [6, 'یکشنبه'], [0, 'دوشنبه'], [1, 'سه‌شنبه'], [2, 'چهارشنبه'], [3, 'پنجشنبه'], [4, 'جمعه']]

export default function TrackingSettings() {
  const q = useQuery({ queryKey: ['tracking-cfg'], queryFn: () => get<Cfg>('/settings/tracking').catch(() => null) })
  const [c, setC] = useState<Cfg | null>(null)
  useEffect(() => { if (q.data) setC(q.data) }, [q.data])
  const save = useMutation({ mutationFn: (v: Cfg) => send('/settings/tracking', v, 'PUT') })
  if (!q.data || !c) return null
  const num = (k: keyof Cfg, label: string) => (
    <label className="flex flex-col gap-1">{label}<input className="inp" type="number" value={Number(c[k])} onChange={e => setC({ ...c, [k]: Number(e.target.value) })} /></label>
  )
  return (
    <Card title="ردیابی و حریم خصوصی">
      <div className="flex flex-col gap-2">
        <label className="flex items-center gap-2"><input type="checkbox" checked={c.enabled} onChange={e => setC({ ...c, enabled: e.target.checked })} />ردیابی فعال</label>
        <div className="grid gap-2 sm:grid-cols-2">
          <label className="flex flex-col gap-1">شروع ساعت کاری (HH:MM)<input className="inp" dir="ltr" value={c.work_start} onChange={e => setC({ ...c, work_start: e.target.value })} /></label>
          <label className="flex flex-col gap-1">پایان ساعت کاری (HH:MM)<input className="inp" dir="ltr" value={c.work_end} onChange={e => setC({ ...c, work_end: e.target.value })} /></label>
        </div>
        <div className="flex flex-wrap gap-3">{DAYS.map(([k, n]) => (
          <label key={k} className="flex items-center gap-1"><input type="checkbox" checked={c.work_days.includes(k)} onChange={e => setC({ ...c, work_days: e.target.checked ? [...c.work_days, k] : c.work_days.filter(x => x !== k) })} />{n}</label>
        ))}</div>
        <div className="grid gap-2 sm:grid-cols-2">{num('interval_s', 'فاصلهٔ ثبت (ثانیه)')}{num('min_distance_m', 'حداقل جابجایی (متر)')}{num('retention_days', 'نگهداری (روز)')}{num('tz_offset_min', 'اختلاف ساعت از UTC (دقیقه)')}</div>
        {save.error != null && <ErrorBox error={save.error} />}{save.isSuccess && <p role="status" className="text-ok">تنظیمات ذخیره شد</p>}
        <Btn disabled={save.isPending} onClick={() => save.mutate(c)}>ذخیره</Btn>
        <small className="text-mut">نقاط خارج از ساعت/روز کاری هرگز ذخیره نمی‌شوند؛ مشاهدهٔ مسیر دیگران در حسابرسی ثبت می‌شود.</small>
      </div>
    </Card>
  )
}

