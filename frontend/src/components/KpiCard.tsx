import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'
import { faDigits, faMoney } from '../lib/fa'
import { Icon } from './Icon'

type Props = { label: string; value: number | string; money?: boolean; to?: string; onClick?: () => void; sub?: string; icon?: string; tone?: 'g' | 'b' | 'p' | 'o' | 'r' | 't'; badge?: ReactNode }
export function KpiCard({ label, value, money, to, onClick, sub, icon = 'doc', tone = 'b', badge }: Props) {
  const body = (
    <>
      <div className={`ik ${tone}`}><Icon n={icon} /></div>
      <small>{label}</small>
      <b>{money ? faMoney(value) : faDigits(Number(value).toLocaleString('en-US'))}{money && <span className="unit">تومان</span>}</b>
      {badge}
      {sub && <small>{sub}</small>}
    </>
  )
  const cls = 'cd k'
  if (to) return <Link to={to} className={`${cls} hover:border-bl`}>{body}</Link>
  if (onClick) return <button type="button" onClick={onClick} className={`${cls} w-full hover:border-bl`}>{body}</button>
  return <div className={cls}>{body}</div>
}
