import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { get, send } from '../../lib/api'
import { applyTokens, applyDefaultMode, type ThemeCfg } from '../../lib/tokens'
import { applyTheme, currentTheme } from '../../lib/theme'
import { faDigits } from '../../lib/fa'
import { Btn, Card, ErrorBox, Spinner } from '../ui'

/** ظاهر پنل: رنگ اصلی، گردی گوشه‌ها، اندازهٔ متن و حالت پیش‌فرض تم (برای همهٔ کاربران شرکت) */
export default function ThemeSettings() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['theme'], queryFn: () => get<ThemeCfg>('/settings/theme'), retry: false })
  const [t, setT] = useState<ThemeCfg | null>(null), [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  useEffect(() => { if (q.data) setT(q.data) }, [q.data])
  if (q.isLoading) return <Spinner />
  if (q.error) return <ErrorBox error={q.error} />
  if (!t) return null
  const set = (p: Partial<ThemeCfg>) => { const n = { ...t, ...p }; setT(n); applyTokens(n) }
  async function save() {
    try { const r = await send<ThemeCfg>('/settings/theme', t, 'PUT'); applyTokens(r); applyDefaultMode(r.mode); qc.invalidateQueries({ queryKey: ['theme'] }); setMsg({ ok: true, text: 'ذخیره شد' }) }
    catch (x) { setMsg({ ok: false, text: (x as Error).message }) }
  }
  return (
    <Card title="ظاهر و تم">
      <div className="flex flex-col gap-3">
        <label className="flex flex-col gap-1">رنگ اصلی<input className="inp" type="color" value={t.color} onChange={e => set({ color: e.target.value })} /></label>
        <label className="flex flex-col gap-1">گردی گوشه‌ها: {faDigits(t.radius)} پیکسل<input type="range" min={6} max={28} value={t.radius} onChange={e => set({ radius: Number(e.target.value) })} /></label>
        <label className="flex flex-col gap-1">اندازهٔ متن: {faDigits(t.font_scale)}٪<input type="range" min={90} max={120} value={t.font_scale} onChange={e => set({ font_scale: Number(e.target.value) })} /></label>
        <label className="flex flex-col gap-1">حالت پیش‌فرض
          <select className="inp" value={t.mode} onChange={e => setT({ ...t, mode: e.target.value as ThemeCfg['mode'] })}>
            <option value="system">مطابق سیستم</option><option value="dark">تیره</option><option value="light">روشن</option>
          </select>
        </label>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-mut">تم این مرورگر:</span>
          <Btn variant="ghost" onClick={() => { applyTheme(currentTheme() === 'dark' ? 'light' : 'dark'); setT({ ...t }) }}>{currentTheme() === 'dark' ? 'تیره (تغییر به روشن)' : 'روشن (تغییر به تیره)'}</Btn>
        </div>
        {msg && <p role={msg.ok ? 'status' : 'alert'} className={msg.ok ? 'text-ok' : 'text-bad'}>{msg.text}</p>}
        <Btn onClick={save}>ذخیره برای همهٔ کاربران</Btn>
      </div>
    </Card>
  )
}
