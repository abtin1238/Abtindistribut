# پرامپت تکمیل باقی‌ماندهٔ Abtin Distribution Suite

> همراه `MASTER_BUILD_PROMPT.md` و پوشهٔ پروژه به عامل کدنویسی بدهید. هر مرحله فقط با تست سبز و گزارش (قالب بخش ۹ پرامپت جامع) تمام می‌شود؛ حدس نزن، اول کد را بخوان.

## قوانین
- پروژه بالغ است؛ هیچ ماژول موجودی را بازنویسی نکن. فقط شکاف‌ها را ببند و رفتار فعلی را با تست حفظ کن.
- پول فقط `Decimal`، محاسبات فقط در Backend، هر endpoint با Permission + Audit + tenant، حذف مالی فقط با سند معکوس.
- هر مایگریشن Alembic روی SQLite و PostgreSQL 16 اجرا و تست شود. هر چیزی که اجرا نکردی صریحاً «اجرا نشد» گزارش بده.

## مرحله A — اعتبارسنجی پایه (قبل از هر قابلیت جدید)
1. `pip install -r requirements-dev.txt && pytest -q` را روی SQLite و روی PostgreSQL 16 (`DATABASE_URL`) اجرا کن؛ همهٔ شکست‌ها را رفع کن (به‌ویژه `test_stage15/16/18/19*/20*`, `test_costing_flow`, `test_reports_v2`, `test_gps`).
2. `alembic upgrade head` روی دیتابیس خالی + `downgrade -1` + `upgrade head`.
3. تست سازگاری Postgres: هر `DISTINCT` روی ستون JSON، `GROUP BY` ناقص، مقایسهٔ تاریخ؛ CI با ماتریس `sqlite|postgres` برای کل pytest.
4. `ruff`, `mypy` (حداقل core/services)، پوشش ≥۸۰٪ برای `services/accounting`، `inventory`، `sales`.
5. تست E2E بک‌اند: مشتری ← کالا ← خرید/رسید ← سفارش ← رزرو ← تأیید ← پخش (کامل/ناقص/ناموفق) ← پرداخت/چک ← سند ← تراز ← گزارش ← داشبورد؛ ادعا: تراز متوازن و ارقام داشبورد = ارقام دفتر.

## مرحله B — شکاف‌های بک‌اند (هرکدام: مدل + مایگریشن + API + تست + UI)
1. **انبار:** انبارگردانی (`StockCount`)، بچ/انقضا (`Batch`، FEFO)، ضرایب تبدیل واحد (`UnitConversion`)، بارکد.
2. **قیمت:** `PriceList`، `Campaign` کدی/زمان‌دار، سقف تخفیف دستی به‌ازای نقش، لاگ تغییر قاعده.
3. **خرید:** سفارش/پیش‌فاکتور خرید، `PurchaseReceipt` جزئی، `PurchaseReturn` با بازمحاسبهٔ میانگین بها، `CostAllocation` (گمرک/حمل جدا).
4. **خزانه:** مغایرت‌گیری بانکی، کارمزد، هزینهٔ چک برگشتی، اعلان خودکار سررسید (۷/۳/۱ روز)، مانع مانده منفی هنگام وصول چک پرداختی، چاپ چک.
5. **حقوق/HR:** شیفت و چارت، قرارداد کارمند، بیمه/مالیات پارامتری، اضافه‌کاری، پورسانت بازاریاب از فروش واقعی، مانده مرخصی، فیش PDF.
6. **حسابداری:** `PostingTemplate` قابل‌تنظیم، `FiscalYear`، واحد پول در تنظیمات شرکت، حذف معاملات بین‌شرکتی در Consolidation.
7. **فاکتور:** PDF قالب‌دار (لوگو/سربرگ)، گزارش‌های PDF با سربرگ، UI ذخیرهٔ فیلتر گزارش‌ها.
8. **امنیت/زیرساخت:** Refresh token چرخشی (`RefreshToken`) + Access کوتاه، Redis برای rate limit/idempotency/صف (ARQ یا Celery) به‌جای حافظهٔ پروسه، ذخیره‌ساز فایل S3-compatible، `sort`/`q` یکسان روی همهٔ لیست‌ها، منبع رویدادهای وبهوک `invoice.created`/`payment.created`.

## مرحله C — فرانت‌اند: مهاجرت تدریجی به React + TypeScript + Vite + Tailwind
تصمیم: **strangler** — اپ جدید در `frontend/` (از قبل اسکلت دارد: Vite، Tailwind، TanStack Query، RTL، صفحهٔ ورود و مشتریان، Vitest، Playwright) روی `/app` سرو می‌شود؛ وب قدیمی `/web` تا پایان مهاجرت کار می‌کند.
1. `cd frontend && npm install && npm run typecheck && npm test && npm run build` را اجرا و رفع کن؛ `uvicorn` را بالا بیاور و `E2E_PASS=... npx playwright test` را اجرا کن.
2. به‌ترتیب اولویت صفحه‌ها را منتقل کن: ورود/نشست/تغییر شرکت ← داشبورد ← مشتریان ← کالا و قیمت ← انبار ← سفارش و فاکتور ← خزانه/چک/بانک ← خرید ← حسابداری ← گزارش‌ها ← HR ← تنظیمات/کاربران/نقش‌ها. هر صفحه: Loading/Error/Empty، فرم با اعتبارسنجی، جدول با صفحه‌بندی/مرتب‌سازی سمت سرور (`X-Total-Count`)، تأیید قبل از عمل خطرناک، تاریخ شمسی و ارقام فارسی، تم روشن/تاریک.
3. برای هر صفحه: حداقل یک تست Vitest (کامپوننت) و یک سناریوی Playwright؛ نوع‌ها از OpenAPI تولید شود (`openapi-typescript`).
4. توکن نباید در `localStorage` باشد (حافظه یا کوکی HttpOnly پس از Refresh token).
5. وقتی همهٔ منوها منتقل و تست‌ها سبز شد: `web/js/app.js` و بقیهٔ وب قدیمی و `tests/ui/test_web_ui.py` را حذف کن، `/` را به `/app/` ریدایرکت کن، `Dockerfile` را multi-stage (build فرانت) کن، CI را روی `npm run build && npm test && playwright` سبز نگه دار.
6. دو اپ موبایل (`mobile/visitor`, `mobile/driver`) را به PWA مبتنی بر همین React ببر با IndexedDB + صف sync و تست آفلاین/تعارض.

## مرحله D — Production
- Dockerfile/compose: Postgres فقط در شبکهٔ داخلی، Redis، HTTPS، `API_DOCS_ENABLED` آگاهانه، Seed فقط dev.
- backup روزانه + تست بازیابی در CI، متریک Prometheus، `/health` و `/ready`، Sentry/OTel.
- تست امنیت: SQLi/XSS/CSRF/IDOR/brute-force/آپلود مخرب، `pip-audit`، `npm audit`.
- مستندات: AUDIT، ARCHITECTURE، API، RUNBOOK، راهنمای هر نقش (و `docs/COVERAGE.md` را به‌روز کن).

## تعریف «تمام‌شده»
چک‌لیست بخش ۱۰ `MASTER_BUILD_PROMPT.md` + `pytest` سبز روی Postgres + Vitest/Playwright سبز در CI + حذف کامل وب قدیمی.
