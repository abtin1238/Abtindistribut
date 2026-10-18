import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import L from '../lib/leafletGlobal'
import 'leaflet/dist/leaflet.css'
import { get } from '../lib/api'
import { faDigits } from '../lib/fa'
import { Link } from 'react-router-dom'

type Pt = { lat?: number | null; lng?: number | null; name?: string; user_id?: number; driver_id?: number; status?: string }
const has = (x: Pt) => x.lat != null && x.lng != null
const dot = (tone: string) => L.divIcon({ className: '', html: `<i class="pin ds-pin-color" data-tone="${tone}"></i>`, iconSize: [14, 14], iconAnchor: [7, 7] })
const label = (t: string) => { const s = document.createElement('span'); s.textContent = t; return s }
const arr = <T,>(p: string) => get<T[]>(p).catch(() => [] as T[])

/** کارت «نمای کلی مسیرها و موقعیت‌ها» داشبورد */
export function DashMap() {
  const el = useRef<HTMLDivElement>(null), map = useRef<L.Map | null>(null), groups = useRef<Record<string, L.LayerGroup>>({})
  const cu = useQuery({ queryKey: ['dm-cu'], queryFn: () => arr<Pt>('/customers'), retry: false })
  const vi = useQuery({ queryKey: ['dm-vi'], queryFn: () => arr<Pt>('/visits/today'), retry: false })
  const de = useQuery({ queryKey: ['dm-de'], queryFn: () => arr<Pt>('/deliveries'), retry: false })
  const wh = useQuery({ queryKey: ['dm-wh'], queryFn: () => arr<Pt>('/warehouses'), retry: false })
  const fit = () => {
    const p: L.LatLng[] = []
    Object.values(groups.current).forEach(g => g.eachLayer(l => { if (l instanceof L.Marker) p.push(l.getLatLng()) }))
    if (p.length && map.current) map.current.fitBounds(L.latLngBounds(p).pad(0.2), { maxZoom: 15 })
  }
  useEffect(() => {
    if (!el.current) return
    const m = L.map(el.current).setView([35.7, 51.4], 11)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap' }).addTo(m)
    map.current = m
    groups.current = { c: L.layerGroup().addTo(m), v: L.layerGroup().addTo(m), d: L.layerGroup().addTo(m) }
    setTimeout(() => m.invalidateSize(), 150)
    return () => { m.remove(); map.current = null }
  }, [])
  useEffect(() => {
    const g = groups.current
    if (!map.current || !g.c) return
    Object.values(g).forEach(x => x.clearLayers())
    ;(cu.data ?? []).filter(has).forEach(x => L.marker([x.lat!, x.lng!], { icon: dot('warn') }).bindPopup(label(x.name ?? '')).addTo(g.c))
    ;(vi.data ?? []).filter(has).forEach(x => L.marker([x.lat!, x.lng!], { icon: dot('ok') }).addTo(g.v))
    ;(de.data ?? []).filter(has).forEach(x => L.marker([x.lat!, x.lng!], { icon: dot('info') }).addTo(g.d))
    fit()
  }, [cu.data, vi.data, de.data])
  const filter = (v: string) => Object.entries(groups.current).forEach(([k, g]) => { if (v === 'all' || v === k) map.current?.addLayer(g); else map.current?.removeLayer(g) })
  const active = (de.data ?? []).filter(x => ['assigned', 'out_for_delivery'].includes(String(x.status)))
  const legend: [string, string, number][] = [
    ['ok', 'بازاریاب فعال', new Set((vi.data ?? []).map(x => x.user_id)).size],
    ['info', 'مأمور پخش', new Set(active.map(x => x.driver_id)).size],
    ['warn', 'مشتری', (cu.data ?? []).length],
    ['pur', 'انبار', (wh.data ?? []).length],
  ]
  return (
    <section className="cd">
      <header>
        <h3>نمای کلی مسیرها و موقعیت‌ها</h3>
        <select aria-label="فیلتر نقشه" onChange={e => filter(e.target.value)}>
          <option value="all">همه</option><option value="c">مشتری</option><option value="v">بازاریاب</option><option value="d">مأمور پخش</option>
        </select>
      </header>
      <div className="mc">
        <div className="lg">
          {legend.map(([t, text, n]) => <div key={t}><span><i className="ds-dot" data-tone={t} />{text}</span><b>{faDigits(n)}</b></div>)}
          <button type="button" className="btn" onClick={fit}>مشاهده تمام موقعیت‌ها ←</button>
          <Link to="/map" className="ds-link">نقشه و GPS</Link>
        </div>
        <div className="map-card" ref={el} />
      </div>
    </section>
  )
}
