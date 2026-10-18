import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { get, send } from '../lib/api'
import { Btn, Card, Empty, ErrorBox, Spinner } from '../components/ui'
import { FormDialog } from '../components/FormDialog'
import type { Field } from '../lib/types'

type Company = { id: number; name: string; code: string; parent_company_id: number | null }
type Branch = { id: number; company_id: number; name: string; address?: string }
type Org = { group: { name: string }; companies: Company[]; branches: Branch[] }

export default function Organizations() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['organizations'], queryFn: () => get<Org>('/organizations') })
  const [dlg, setDlg] = useState<null | 'company' | 'branch'>(null)
  if (q.isLoading) return <Spinner />
  if (q.error) return <ErrorBox error={q.error} />
  const d = q.data!
  const name = (id: number | null) => d.companies.find(c => c.id === id)?.name ?? '—'
  const companyOpts = d.companies.map(c => ({ value: c.id, label: c.name }))
  const companyFields: Field[] = [
    { name: 'name', label: 'نام', required: true }, { name: 'code', label: 'کد', required: true },
    { name: 'parent_company_id', label: 'شرکت والد (خالی = ریشه)', type: 'select', options: companyOpts },
  ]
  const branchFields: Field[] = [
    { name: 'company_id', label: 'شرکت', type: 'select', options: companyOpts, required: true },
    { name: 'name', label: 'نام شعبه', required: true }, { name: 'address', label: 'نشانی', type: 'textarea' },
  ]
  const done = () => qc.invalidateQueries({ queryKey: ['organizations'] }).then(() => qc.invalidateQueries({ queryKey: ['me'] }))
  return (
    <section className="mx-auto flex max-w-4xl flex-col gap-4 p-4">
      <h2 className="text-lg font-bold">هلدینگ و شرکت‌ها — گروه: {d.group.name}</h2>
      <Card title="شرکت‌ها">
        <Btn className="mb-2" onClick={() => setDlg('company')}>شرکت جدید</Btn>
        {!d.companies.length ? <Empty>شرکتی ثبت نشده است.</Empty> : (
          <table className="w-full text-sm"><thead><tr><th className="th">شرکت</th><th className="th">کد</th><th className="th">شرکت والد</th></tr></thead>
            <tbody>{d.companies.map(c => <tr key={c.id}><td className="td">{c.name}</td><td className="td" dir="ltr">{c.code}</td><td className="td">{c.parent_company_id ? name(c.parent_company_id) : 'ریشه'}</td></tr>)}</tbody></table>
        )}
      </Card>
      <Card title="شعب">
        <Btn className="mb-2" disabled={!d.companies.length} onClick={() => setDlg('branch')}>شعبه جدید</Btn>
        {!d.branches.length ? <Empty>شعبه‌ای ثبت نشده است.</Empty> : (
          <table className="w-full text-sm"><thead><tr><th className="th">شعبه</th><th className="th">شرکت</th><th className="th">نشانی</th></tr></thead>
            <tbody>{d.branches.map(b => <tr key={b.id}><td className="td">{b.name}</td><td className="td">{name(b.company_id)}</td><td className="td">{b.address || '—'}</td></tr>)}</tbody></table>
        )}
      </Card>
      {dlg === 'company' && <FormDialog title="شرکت جدید" fields={companyFields} onClose={() => setDlg(null)}
        onSubmit={async v => { await send('/organizations/company', { ...v, parent_company_id: v.parent_company_id ?? null }); await done() }} />}
      {dlg === 'branch' && <FormDialog title="شعبه جدید" fields={branchFields} onClose={() => setDlg(null)}
        onSubmit={async v => { await send('/organizations/branch', v); await done() }} />}
    </section>
  )
}
