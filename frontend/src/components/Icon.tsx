const IC: Record<string, string> = {
  home: 'M3 11l9-8 9 8v10h-6v-6H9v6H3z',
  building: 'M4 21V4h10v17M14 9h6v12M8 8h2M8 12h2M8 16h2',
  users: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8',
  cart: 'M3 3h2l2.4 12.4h10.3L20 7H6M9 21h.01M18 21h.01',
  box: 'M21 8l-9-5-9 5v8l9 5 9-5zM3 8l9 5 9-5M12 13v8',
  truck: 'M1 3h13v13H1zM14 8h4l3 3v5h-7M6 19.5h.01M17 19.5h.01',
  wallet: 'M3 7h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM3 7l12-4v4M17 14h.01',
  chart: 'M3 3v18h18M7 15l4-4 3 3 5-6',
  gear: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2',
  search: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16M21 21l-4.3-4.3',
  bell: 'M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10 21h4',
  trend: 'M3 17l6-6 4 4 8-8M15 7h6v6',
  doc: 'M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6M8 13h8M8 17h5',
  alert: 'M12 3l10 18H2zM12 10v5M12 18h.01',
  cal: 'M3 5h18v16H3zM3 10h18M8 3v4M16 3v4',
  check: 'M5 12.5l4.5 4.5L19 7.5',
  menu: 'M4 7h16M4 12h16M4 17h16',
  chev: 'M9 6l6 6-6 6',
  moon: 'M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z',
  bars: 'M5 21V10M12 21V4M19 21v-7',
  pie: 'M21 12A9 9 0 1 1 12 3v9zM15 3.5A9 9 0 0 1 20.5 9H15z',
  shield: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z',
  card: 'M3 6h18v12H3zM3 10h18M7 15h3',
}
export type IconName = keyof typeof IC
export function Icon({ n, className = 'ic' }: { n: string; className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={IC[n] ?? IC.doc} />
    </svg>
  )
}
export const Logo = ({ size = 40 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true"><path d="M20 3L3 36h9l8-16 8 16h9z" fill="var(--bl)" /><path d="M20 20l-5 10h10z" fill="var(--bl2)" /></svg>
)
