import type { ButtonHTMLAttributes, ReactNode } from 'react'
export function Btn({ variant = 'primary', className = '', ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'ghost' | 'danger' }) {
  const c = variant === 'primary' ? 'btn-pri' : variant === 'danger' ? 'btn-dng' : 'btn-gho'
  return <button {...p} className={`rounded-ds-sm px-3 py-1.5 text-sm disabled:opacity-50 ${c} ${className}`} />
}
export const Spinner = () => <p role="status" className="p-4 text-mut">در حال بارگذاری…</p>
export const ErrorBox = ({ error }: { error: unknown }) => <p role="alert" className="rounded-ds-sm bg-bad-soft p-3 text-bad">{(error as Error)?.message ?? String(error)}</p>
export const Empty = ({ children }: { children: ReactNode }) => <p className="p-6 text-center text-mut">{children}</p>
export const Card = ({ title, children }: { title?: string; children: ReactNode }) => (
  <section className="cd">{title && <header><h3>{title}</h3></header>}{children}</section>
)
