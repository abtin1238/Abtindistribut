import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import L from '../lib/leafletGlobal'
import 'leaflet/dist/leaflet.css'
import 'leaflet.markercluster'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'
import { Link } from 'react-router-dom'
import { get } from '../lib/api'
import { faDigits } from '../lib/fa'
import { Btn, Card, ErrorBox, Spinner } from '../components/ui'

type GpsUser = { id: number; name: string; kind: string }
type Cust = { lat: number; lng: number; name: string; code: string; region?: string }
type CustRes = { customers: Cust[]; truncated: boolean; without_gps: number }
type LiveRes = { active: boolean; users: { lat: number; lng: number; name: string; kind: string; age_s: number }[] }
type Track = {
  user: { name: string }; day: string; point_count: number; distance_km: number; first_at?: string; last_at?: string; radius_m: number
  points: { lat: number; lng: number; t: string }[]
  visits: { customer_name: string; started_at: string; ended_at: string; lat: number | null; lng: number | null; gps_status?: string; gps_presence: boolean | null; presence_minutes?: number }[]
  deliveries: { customer_name: string; order_number: string; status: string; at: string; lat: number | null; lng: number | null; gps_status?: string }[]
  stays: { customer_name: string; enter: string; exit: string; minutes: number; min_distance_m: number }[]
}

const KIND: Record<string, [string, string]> = { visitor: ['#16a34a', 'بازاریاب'], driver: ['#2563eb', 'مأمور پخش'], other: ['#d97706', 'سایر'] }
const tm = (s?: string) => (s ? new Date(s).toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' }) : '—')
const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }
const dot = (color: string) => L.divIcon({ className: '', html: `<i style="display:block;width:14px;height:14px;border-radius:50%;background:${color};border:2px solid #fff;box-shadow:0 0 3px #0006"></i>`, iconSize: [14, 14], iconAnchor: [7, 7] })
/** پاپ‌آپ با DOM امن ساخته می‌شود (textContent)؛ هیچ رشتهٔ HTML از داده‌ی کاربر تولید نمی‌شود. */
const popup = (...lines: string[]) => { const el = document.createElement('div'); lines.forEach((t, i) => { const e = document.createElement(i === 0 ? 'b' : 'div'); e.textContent = t; el.appendChild(e) }); return el }

const T = ({ head, rows, empty }: { head: string[]; rows: React.ReactNode[][]; empty: string }) => (
  <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr>{head.map(h => <th key={h} className="th">{h}</th>)}</tr></thead>
    <tbody>{rows.length ? rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j} className="td">{c}</td>)}</tr>) : <tr><td className="td" colSpan={head.length}>{empty}</td></tr>}</tbody></table></div>
)

export default function MapPage() {
  const box = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const layers = useRef<{ cust: L.MarkerClusterGroup; live: L.LayerGroup; track: L.LayerGroup } | null>(null)
  const [bbox, setBbox] = useState<string | undefined>()
  const [uid, setUid] = useState(''), [day, setDay] = useState(today), [trackKey, setTrackKey] = useState<[string, string] | null>(null)
  const users = useQuery({ queryKey: ['gps-users'], queryFn: () => get<GpsUser[]>('/gps/users').catch(() => [] as GpsUser[]) })
  const cust = useQuery({ queryKey: ['gps-customers', bbox], queryFn: () => get<CustRes>(`/gps/customers?limit=5000${bbox ? `&bbox=${bbox}` : ''}`) })
  const live = useQuery({ queryKey: ['gps-live'], queryFn: () => get<LiveRes>('/gps/live?minutes=15'), refetchInterval: 30_000 })
  const track = useQuery({ queryKey: ['gps-track', trackKey], enabled: !!trackKey, queryFn: () => get<Track>(`/gps/track?user_id=${encodeURIComponent(trackKey![0])}&day=${encodeURIComponent(trackKey![1])}`) })
  const truncated = useRef(false)
  truncated.current = !!cust.data?.truncated

  useEffect(() => {
    if (!box.current || map.current) return
    const m = L.map(box.current).setView([35.7, 51.4], 11)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap' }).addTo(m)
    layers.current = { cust: L.markerClusterGroup({ chunkedLoading: true, maxClusterRadius: 50 }).addTo(m), live: L.layerGroup().addTo(m), track: L.layerGroup().addTo(m) }
    m.on('moveend', () => { if (truncated.current) { const b = m.getBounds(); setBbox([b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].join(',')) } })
    map.current = m
    setTimeout(() => m.invalidateSize(), 150)
    return () => { m.remove(); map.current = null; layers.current = null }
  }, [])

  useEffect(() => {
    const l = layers.current, d = cust.data
    if (!l || !d) return
    l.cust.clearLayers()
    d.customers.forEach(c => L.marker([c.lat, c.lng], { icon: dot('#d97706') }).bindPopup(popup(c.name, `${c.code} ${c.region ?? ''}`)).addTo(l.cust))
    if (!bbox && d.customers.length) map.current?.fitBounds(L.latLngBounds(d.customers.map(c => [c.lat, c.lng] as [number, number])).pad(0.1), { maxZoom: 14 })
  }, [cust.data, bbox])

  useEffect(() => {
    const l = layers.current
    if (!l || !live.data) return
    l.live.clearLayers()
    if (!live.data.active) return
    live.data.users.forEach(u => { const k = KIND[u.kind] ?? KIND.other; L.marker([u.lat, u.lng], { icon: dot(k[0]) }).bindPopup(popup(u.name, k[1], `${faDigits(Math.round(u.age_s / 60))} دقیقه پیش`)).addTo(l.live) })
  }, [live.data])

  useEffect(() => {
    const l = layers.current, d = track.data
    if (!l || !d) return
    l.track.clearLayers()
    const ll = d.points.map(p => [p.lat, p.lng] as [number, number])
    if (ll.length) {
      L.polyline(ll, { color: '#2563eb', weight: 4, opacity: 0.85 }).addTo(l.track)
      L.marker(ll[0], { icon: dot('#16a34a') }).bindPopup(popup(`شروع: ${tm(d.points[0].t)}`)).addTo(l.track)
      L.marker(ll[ll.length - 1], { icon: dot('#dc2626') }).bindPopup(popup(`آخرین موقعیت: ${tm(d.points[d.points.length - 1].t)}`)).addTo(l.track)
      map.current?.fitBounds(L.latLngBounds(ll).pad(0.2), { maxZoom: 16 })
    }
    d.visits.forEach(v => { if (v.lat != null && v.lng != null) L.circleMarker([v.lat, v.lng], { radius: 7, color: '#7c3aed', fillOpacity: 0.8 }).bindPopup(popup(`ویزیت ${v.customer_name}`, `${tm(v.started_at)}–${tm(v.ended_at)}`)).addTo(l.track) })
    d.deliveries.forEach(v => { if (v.lat != null && v.lng != null) L.circleMarker([v.lat, v.lng], { radius: 7, color: '#d97706', fillOpacity: 0.8 }).bindPopup(popup(`تحویل ${v.customer_name} (${v.order_number})`, tm(v.at))).addTo(l.track) })
  }, [track.data])

  const d = track.data
  return (
    <section className="mx-auto flex max-w-6xl flex-col gap-3 p-4">
      <div className="flex items-center gap-2"><h2 className="me-auto text-lg font-bold">نقشه و GPS</h2><Link to="/settings?tab=tracking" className="ds-link text-sm">تنظیمات ردیابی ←</Link></div>
      <Card>
        <div className="flex flex-wrap items-end gap-2">
          <label className="flex flex-col gap-1">کاربر
            <select className="inp w-auto" value={uid} onChange={e => setUid(e.target.value)}><option value="">— انتخاب —</option>{users.data?.map(u => <option key={u.id} value={u.id}>{u.name} — {(KIND[u.kind] ?? KIND.other)[1]}</option>)}</select></label>
          <label className="flex flex-col gap-1">روز<input className="inp w-auto" type="date" value={day} onChange={e => setDay(e.target.value)} /></label>
          <Btn disabled={!uid || !day} onClick={() => setTrackKey([uid, day])}>نمایش مسیر روز</Btn>
          <Btn variant="ghost" onClick={() => live.refetch()}>به‌روزرسانی موقعیت زنده</Btn>
        </div>
        <p className="mt-2 text-sm text-mut">
          {live.data && (live.data.active ? `موقعیت زنده (۱۵ دقیقهٔ اخیر): ${faDigits(live.data.users.length)} نفر` : 'خارج از ساعت کاری؛ ردیابی زنده غیرفعال است.')}
          {cust.data && ` — مشتری روی نقشه: ${faDigits(cust.data.customers.length)}${cust.data.truncated ? ' (محدودشده؛ نقشه را بزرگ‌نمایی کنید)' : ''} — بدون مختصات: ${faDigits(cust.data.without_gps)}`}
        </p>
        {(cust.error ?? live.error) != null && <ErrorBox error={cust.error ?? live.error} />}
      </Card>
      <div ref={box} role="application" aria-label="نقشه" className="h-[480px] w-full rounded-lg border border-bd " />
      {track.isLoading && <Spinner />}{track.error != null && <ErrorBox error={track.error} />}
      {d && (
        <>
          <Card><b>{d.user.name}</b> — {d.day} — {faDigits(d.point_count)} نقطه — مسافت: {faDigits(d.distance_km)} کیلومتر — از {tm(d.first_at)} تا {tm(d.last_at)} <small className="text-mut">(شعاع حضور: {faDigits(d.radius_m)} متر)</small></Card>
          <Card title="زمان حضور نزد مشتری (از GPS)"><T head={['مشتری', 'ورود', 'خروج', 'مدت (دقیقه)', 'نزدیک‌ترین فاصله (متر)']} empty="حضور ≥ ۳ دقیقه‌ای نزد مشتری ثبت نشده"
            rows={d.stays.map(s => [s.customer_name, tm(s.enter), tm(s.exit), faDigits(s.minutes), faDigits(Math.round(s.min_distance_m))])} /></Card>
          <Card title="ویزیت‌های ثبت‌شده و تطبیق با GPS"><T head={['مشتری', 'شروع', 'پایان', 'وضعیت GPS ویزیت', 'حضور واقعی (GPS)']} empty="ویزیتی نیست"
            rows={d.visits.map(v => [v.customer_name, tm(v.started_at), tm(v.ended_at), v.gps_status || '—', v.gps_presence == null ? 'بدون داده‌ی مسیر' : v.gps_presence ? `✓ ${faDigits(v.presence_minutes ?? 0)} دقیقه` : '✗ حضور ثبت نشد'])} /></Card>
          <Card title="تحویل‌ها"><T head={['سفارش', 'مشتری', 'وضعیت', 'زمان', 'GPS']} empty="تحویلی نیست"
            rows={d.deliveries.map(v => [v.order_number, v.customer_name, v.status, tm(v.at), v.gps_status || '—'])} /></Card>
        </>
      )}
    </section>
  )
}
