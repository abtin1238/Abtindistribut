import { faCompact, faDigits, faMoney, jalaliMD } from '../lib/fa'

export type Point = { day: string; total: number | string }
const cmp = (v: number) => { const c = faCompact(v); return c.unit ? `${c.n} ${c.unit}` : c.n }
const TONES = ['var(--ok)', 'var(--info)', 'var(--warn)', 'var(--pink)', 'var(--pur)']

/** نمودار ناحیه‌ای منحنی (همان ظاهر داشبورد طراحی‌شده) */
export function LineChart({ series, label = 'روند فروش روزانه' }: { series: Point[]; label?: string }) {
  if (!series.length || series.every(x => !Number(x.total))) return <p className="empty">در این بازه فروشی ثبت نشده است.</p>
  const W = 560, H = 220, B = H - 26, n = series.length
  const y = series.map(x => Number(x.total)), mx = Math.max(1, ...y)
  const P = y.map((v, i): [number, number] => [40 + (i * (W - 50)) / Math.max(n - 1, 1), B - (v / mx) * (H - 70)])
  const pk = y.indexOf(Math.max(...y)), step = Math.ceil(n / 7)
  const d = P.reduce((a, [x, yy], i) => (i ? `${a} Q${P[i - 1][0]} ${P[i - 1][1]} ${(x + P[i - 1][0]) / 2} ${(yy + P[i - 1][1]) / 2}` : `M${x} ${yy}`), '') + ` L${P[n - 1][0]} ${P[n - 1][1]}`
  return (
    <svg role="img" aria-label={label} viewBox={`0 0 ${W} ${H}`} className="chart-svg">
      <defs><linearGradient id="agr" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="var(--bl)" stopOpacity=".45" /><stop offset="1" stopColor="var(--bl)" stopOpacity="0" /></linearGradient></defs>
      {[0, 1, 2, 3, 4].map(i => { const yy = B - (i * (H - 70)) / 4; return <g key={i}><line x1="40" x2={W} y1={yy} y2={yy} stroke="var(--bd)" /><text x="34" y={yy + 4} textAnchor="end">{cmp((mx * i) / 4)}</text></g> })}
      <path d={`${d} L${P[n - 1][0]} ${B} L${P[0][0]} ${B}Z`} fill="url(#agr)" />
      <path d={d} fill="none" stroke="var(--bl2)" strokeWidth="3" />
      {series.map((x, i) => (i % step ? null : <text key={x.day} x={P[i][0]} y={H - 6} textAnchor="middle">{jalaliMD(x.day)}</text>))}
      {mx > 1 && <>
        <circle cx={P[pk][0]} cy={P[pk][1]} r="5" fill="#fff" stroke="var(--bl)" strokeWidth="3"><title>{`${jalaliMD(series[pk].day)}: ${faMoney(mx)}`}</title></circle>
        <text x={P[pk][0]} y={P[pk][1] - 12} textAnchor="middle" className="chart-value">{faMoney(mx)}</text>
      </>}
    </svg>
  )
}

export function Donut({ items }: { items: { name: string; value: number }[] }) {
  let c = items.filter(x => x.value > 0).sort((a, b) => b.value - a.value)
  if (c.length > 5) c = [...c.slice(0, 4), { name: 'سایر', value: c.slice(4).reduce((a, x) => a + x.value, 0) }]
  const tot = c.reduce((a, x) => a + x.value, 0)
  if (!tot) return <p className="empty">داده‌ای نیست.</p>
  const r = 62, len = 2 * Math.PI * r
  let off = 0
  return (
    <div className="dn-w">
      <svg role="img" aria-label="سهم دسته‌بندی‌ها از فروش" viewBox="0 0 160 160" className="dn-svg">
        <g transform="rotate(-90 80 80)" fill="none" strokeWidth="18">
          {c.map((x, i) => { const f = x.value / tot, el = <circle key={x.name} cx="80" cy="80" r={r} stroke={TONES[i]} strokeDasharray={`${Math.max(0, f * len - 2)} ${len}`} strokeDashoffset={-off} />; off += f * len; return el })}
        </g>
        <text className="donut-label" x="80" y="74">کل فروش</text>
        <text className="donut-value" x="80" y="96">{cmp(tot)}</text>
      </svg>
      <ul>{c.map((x, i) => (
        <li key={x.name}><i style={{ background: TONES[i] }} />{x.name} <b>{faDigits(Math.round((x.value / tot) * 100))}٪</b></li>
      ))}</ul>
    </div>
  )
}
