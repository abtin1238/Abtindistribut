# ساختار استاندارد فرانت‌اند

## اصل کلی
- استایل‌های وب فقط در `web/styles/` نگهداری می‌شوند.
- استایل مشترک از `web/styles/index.css` بارگذاری می‌شود؛ این فایل ترتیب توکن‌ها، Design System و استایل‌های پوسته را یک‌جا مدیریت می‌کند.
- استایل فاکتور در `web/styles/invoice.css` است و از `invoice-entry.css` برای استفاده از سیستم طراحی مشترک بهره می‌برد.
- استایل‌های اختصاصی PWAها در `mobile/styles/` هستند و از همان ورودی مشترک وب استفاده می‌کنند.
- منطق JavaScript پنل در `web/js/` و منطق مشترک موبایل در `mobile/js/` قرار دارد. اسکریپت‌های اختصاصی صفحات موبایل نیز در همین پوشه هستند.
- `web/js/styles.js` رابط ES Module برای تغییر تم و توکن‌ها است.

## استفاده مجدد از API استایل
```js
import { setTokens, setTheme, cssVar, toggleTheme } from '/web/js/styles.js';

setTokens({ '--bl': '#2f7bff', '--r': '16px' });
setTheme({ color: '#2f7bff', radius: 16, font_scale: 100, mode: 'dark' });
const brandColor = cssVar('--bl');
```

## افزودن استایل یا منطق جدید
1. قوانین مشترک را در فایل‌های `web/styles/` اضافه کنید؛ از ساخت استایل مشابه در صفحات مختلف خودداری کنید.
2. توکن‌های طراحی را در `palette.css` و `theme-tokens.css` تعریف کنید و در کامپوننت‌ها فقط از `var(--token)` استفاده کنید.
3. منطق قابل استفاده مجدد را در ماژول مناسب `web/js/` یا `mobile/js/` قرار دهید.
4. برای کدهای کلاسیک قدیمی ترتیب اسکریپت‌ها را حفظ کنید؛ تبدیل به ES Module باید همراه با بررسی وابستگی‌های سراسری انجام شود.

## نکته
این ساختار، محل فایل‌ها و ورودی استایل را یکپارچه می‌کند؛ مقادیر ظاهری‌ای که هنوز در کدهای قدیمی به‌صورت literal آمده‌اند باید به‌تدریج به توکن‌های CSS منتقل شوند.

### ورودی ماژول‌های قابل import
برای استفاده از API استایل از مسیر عمومی زیر استفاده کنید:
```js
import { setTokens, setTheme, cssVar, toggleTheme } from '/web/js/index.js';
```
اسکریپت‌های کلاسیک قدیمی عمداً به ترتیب فعلی بارگذاری می‌شوند تا وابستگی‌های global آن‌ها نشکند؛ کدهای جدید بهتر است ES Module باشند و از ورودی عمومی استفاده کنند.


## Shared frontend primitives (refactor v2)

- `web/js/shared/core.js` is the single source for API access, HTML escaping, Persian number/money formatting, guarded local-storage reads/writes, local ISO date (`today`) and offline queue synchronization. Classic-script pages consume these via `Shared.*`; mobile exposes compatibility globals from its shared UI adapter only where existing inline handlers need them.
- `web/styles/primitives.css` owns the shared CSS reset and form font inheritance. It is loaded once through `web/styles/index.css`, which is also the shared stylesheet entry point for the mobile PWAs.
- `palette.css` and `theme-tokens.css` remain the single shared source of design tokens; mobile pages import the shared index rather than defining a separate palette.
- Component selectors that intentionally differ by platform (for example `.card` in mobile versus `.cd` in web) remain platform-specific; shared component patterns should use the `ds-*` classes from `design-system.css`.

## یادداشت‌ها
ادیتور متن غنی حذف شد؛ یادداشت‌ها با `<textarea>` ساده ثبت و با `white-space:pre-wrap` (کلاس `.pre-note`) نمایش داده می‌شوند. یادداشت‌های HTMLِ قدیمی هنگام نمایش به متن ساده تبدیل می‌شوند (`plainNote`). پاک‌سازی سمت سرور (`app/core/richtext.py`) باقی است.

## فاکتورها (مرحله ۱۵)
- ستون‌های جدید: `orders.note`, `invoices.note`, `invoices.terms` (مایگریشن `0007` و `ensure_schema`).
- `GET /api/invoices?status&q&start&end&limit` با نام مشتری، شماره سفارش و مانده؛ `PATCH /api/invoices/{id}/note`؛ `GET/PUT /api/settings/invoice-terms`؛ جزئیات فاکتور شامل `returns` و `order_status`.
- پنل: لیست با فیلتر و آمار، دریافت وجه، ابطال، برگشت از فروش، یادداشت، فرم ثبت سفارش و صدور فاکتور؛ چاپ با برگشتی، یادداشت و شرایط.
