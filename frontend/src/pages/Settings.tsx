import { useSearchParams } from 'react-router-dom'
import { can, useMe } from '../lib/useMe'
import BrandSettings from '../components/settings/BrandSettings'
import ThemeSettings from '../components/settings/ThemeSettings'
import NotificationSettings from '../components/settings/NotificationSettings'
import TrackingSettings from '../components/settings/TrackingSettings'
import { FormSection } from '../components/settings/FormSection'

const TABS: { id: string; label: string; perm?: string }[] = [
  { id: 'general', label: 'عمومی و برند' },
  { id: 'appearance', label: 'ظاهر و تم' },
  { id: 'invoice', label: 'فاکتور و مالیات' },
  { id: 'notifications', label: 'اعلان‌ها' },
  { id: 'tracking', label: 'ردیابی و ویزیت', perm: 'gps.read' },
]

/** مرکز تنظیمات: همهٔ تنظیمات سیستم در یک صفحه؛ صفحه‌های دیگر فقط به همین‌جا لینک می‌دهند. */
export default function Settings() {
  const me = useMe(), [sp, setSp] = useSearchParams()
  const tabs = TABS.filter(t => can(me.data, t.perm))
  const tab = tabs.find(t => t.id === sp.get('tab'))?.id ?? 'general'
  return (
    <section className="mx-auto flex max-w-4xl flex-col gap-4 p-4">
      <h2 className="text-lg font-bold">تنظیمات</h2>
      <div role="tablist" aria-label="بخش‌های تنظیمات" className="flex flex-wrap gap-2">
        {tabs.map(t => (
          <button key={t.id} type="button" role="tab" aria-selected={tab === t.id} onClick={() => setSp({ tab: t.id }, { replace: true })}
            className={`rounded-ds-sm px-3 py-1.5 text-sm ${tab === t.id ? 'btn-pri' : 'btn-gho'}`}>{t.label}</button>
        ))}
      </div>
      <div className="flex flex-col gap-4" role="tabpanel">
        {tab === 'general' && <BrandSettings />}
        {tab === 'appearance' && <ThemeSettings />}
        {tab === 'invoice' && <>
          <FormSection title="مالیات" path="/settings/tax" fields={[{ name: 'vat_percent', label: 'درصد ارزش افزوده', type: 'number' }]} />
          <FormSection title="شرایط فاکتور" path="/settings/invoice-terms" fields={[{ name: 'terms', label: 'متن', type: 'textarea' }]} />
        </>}
        {tab === 'notifications' && <NotificationSettings />}
        {tab === 'tracking' && <>
          <TrackingSettings />
          <FormSection title="ویزیت" path="/settings/visit" fields={[{ name: 'radius_m', label: 'شعاع مجاز ثبت ویزیت از مشتری (متر)', type: 'number', hint: 'بین ۱۰ تا ۵۰۰۰ متر' }]} />
        </>}
      </div>
    </section>
  )
}
