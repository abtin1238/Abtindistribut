# مهاجرت پنل به React

## معادل React برای هر صفحهٔ `web/`
| قدیمی (`web/js`) | React (`frontend/src`) |
|---|---|
| app.js (ورود، هدایت نقش) | `pages/Login.tsx` + `lib/roleApp.ts` |
| datatable.js (organizations) | `pages/Organizations.tsx` |
| import.js | `pages/Import.tsx` (بر اساس API واقعی تک‌فایل) |
| map.js | `pages/Map.tsx` (Leaflet + markercluster) |
| search-ui.js | `pages/Search.tsx` |
| notify-ui.js + sw.js | `pages/Notifications.tsx` + `public/sw.js` |
| account-ui.js | `components/AccountDialog.tsx` |
| sales.js (قیف) | `pages/Funnel.tsx` |
| invoice.html / invoice.js | `pages/InvoicePrint.tsx` (مسیر `/app/invoices/:id/print`) |
| dashboard.js | `pages/Dashboard.tsx` (KPI با drill-down، روند و دسته‌بندی از API، فعالیت‌ها) |
| ceo.js | `pages/Ceo.tsx` (کارت‌های drill-down، نقدینگی، چک، کارکنان، هلدینگ، تطبیق دفتر کل) |
| reports.js | `pages/Reports.tsx` (فیلتر اختصاصی هر گزارش، drill-down، Excel/PDF، خروجی پس‌زمینه) |
| datatable.js (audit) | `lib/auditLabels.ts` + منبع `audit` (برچسب فارسی) |
| X-Client: panel (قفل پنل) | `lib/api.ts` |

## شعبه
- `PATCH /api/customers/{id}` (جدید) با همان قواعد محدودیت شعبه‌ی افزودن مشتری؛ تست: `tests/test_customer_update.py` (هنوز اجرا نشده).
- انتخاب شعبه در فرم مشتری، کاربر و انبار و ستون شعبه؛ اکشن «ویرایش» مشتری و «تغییر نقش/شعبه» کاربر.

## هنوز در `web/` مانده (عمداً حذف نشده)
- `web/index.html` اکنون فقط به `/app/` هدایت می‌کند؛ بقیه‌ی `web/js` پنل قدیمی بلااستفاده است و پس از تأیید Playwright حذف می‌شود.
- `web/styles/*` و `web/js/shared/core.js`: اپ‌های موبایل (`mobile/`) از آن‌ها استفاده می‌کنند.
- `/web/` همچنان `home` کاربران پنل در `APP_HOME` است و تست‌های `test_app_routing_branch.py` و `test_invoice_detail.py` به آن وابسته‌اند.
- پس از اجرای موفق build و Playwright، `web/index.html` و `web/js/*` پنل را می‌توان حذف و `APP_HOME['panel']` را به `/app/` تغییر داد.

## یافته‌ها
- `import.js` قدیمی `files` + `overrides` می‌فرستاد، اما `/api/import/*` فقط یک `file` می‌پذیرد؛ صفحهٔ قدیمی با این بک‌اند کار نمی‌کرد.
- چاپ فاکتور در React به `/web/invoice.html` می‌رفت که توکن را از `localStorage['ads_token']` می‌خواند؛ React توکن را در `sessionStorage['abtin_token']` نگه می‌دارد، پس چاپ همیشه «ابتدا وارد شوید» می‌داد.
- `StaticFiles(html=True)` برای `/app/customers` هنگام رفرش ۴۰۴ می‌داد؛ `SPAStaticFiles` در `app/main.py` اضافه شد.
