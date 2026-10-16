import type { ButtonHTMLAttributes, ReactNode } from 'react'
export function Btn({ variant = 'primary', className = '', ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'ghost' | 'danger' }) {
  const c = variant === 'primary' ? 'bg-blue-600 text-white' : variant === 'danger' ? 'bg-red-600 text-white' : 'border border-slate-400'
  return <button {...p} className={`rounded px-3 py-1.5 text-sm disabled:opacity-50 ${c} ${className}`} />
}
export const Spinner = () => <p role="status" className="p-4 text-slate-500">در حال بارگذاری…</p>
export const ErrorBox = ({ error }: { error: unknown }) => <p role="alert" className="rounded bg-red-50 p-3 text-red-700 dark:bg-red-950 dark:text-red-300">{(error as Error)?.message ?? String(error)}</p>
export const Empty = ({ children }: { children: ReactNode }) => <p className="p-6 text-center text-slate-500">{children}</p>
export const Card = ({ title, children }: { title?: string; children: ReactNode }) => (
  <section className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">{title && <h3 className="mb-2 font-semibold">{title}</h3>}{children}</section>
)
