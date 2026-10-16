import type { ReactNode } from 'react'
export type Row = Record<string, any>
export type Kind = 'text' | 'money' | 'num' | 'date' | 'bool' | 'ref'
export type Col = { key: string; label: string; kind?: Kind; ref?: string; render?: (r: Row) => ReactNode }
export type Opt = { value: string | number; label: string }
export type Field = {
  name: string; label: string
  type?: 'text' | 'number' | 'date' | 'select' | 'multi' | 'textarea' | 'checkbox' | 'password'
  required?: boolean; options?: Opt[]
  optionsFrom?: { endpoint: string; value?: string; label?: string }
  def?: string | number | boolean; hidden?: boolean; placeholder?: string
}
export type Action = {
  label: string; danger?: boolean; confirm?: string; fields?: Field[]
  when?: (r: Row) => boolean; run: (r: Row, v: Record<string, unknown>) => Promise<unknown>
}
export type Resource = {
  path: string; title: string; endpoint: string; perm?: string; paged?: boolean; newTo?: string; empty?: string
  columns: Col[]
  create?: { title: string; fields: Field[]; endpoint?: string; method?: string; build?: (v: Record<string, unknown>, ctx: { companyId: number }) => unknown }
  actions?: Action[]
  top?: { label: string; run: () => Promise<unknown> }[]
}
