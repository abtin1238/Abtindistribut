# Abtin Distribution Suite

سیستم مدیریت سرورمحور شرکت پخش بزرگ با ساختار هلدینگ/چندشرکتی.

## معماری
- FastAPI + SQLAlchemy
- PostgreSQL برای Production
- API مرکزی مستند در `/docs`
- پنل وب مدیریت در `/`
- اپ وب/PWA ویزیتور در `/mobile/visitor/`
- اپ وب/PWA مأمور پخش در `/mobile/driver/`
- tenant isolation بر اساس شرکت فعال
- ساختار Group → Company → Branch → Warehouse
- نقش و Permission، Audit Log، CRM، کالا، انبار، فروش، فاکتور، خرید، مالی، خزانه، منابع انسانی، CRM فروش، ویزیت و تحویل

## اجرای Production
```bash
docker compose up -d --build
```
سپس `http://SERVER:8000` و برای مستندات API، `http://SERVER:8000/docs`.

## مهاجرت دیتابیس
پس از هر به‌روزرسانی: `alembic upgrade head` (جزئیات در `docs/MIGRATIONS.md`). مرحله ۱۱ مایگریشن `0002` و مرحله ۱۲ مایگریشن `0003` و تکمیل‌ها مایگریشن `0004` و مرحله ۱۳ (نقشه و GPS) مایگریشن `0005` دارند.

## نقشه و GPS
صفحه‌ی «نقشه و GPS» در پنل وب؛ ردیابی فقط با رضایت کاربر و فقط در ساعات کاری (تنظیم: `PUT /api/settings/tracking`). جزئیات حریم خصوصی در `TODO.md`.

## گزارش‌ها و داشبورد مدیرعامل (مرحله ۱۴)
- منوی «گزارش‌ها»: فروش (کالا/مشتری/فروشنده/منطقه/شعبه/روز/دسته)، مشتریان، انبار (موجودی/کم‌موجودی/راکد/گردش)، بازاریاب، مأمور پخش، سود ناخالص، بدهکاران و Aging، مالی؛ فیلتر شمسی (`jstart`/`jend`)، کاربر، شعبه، منطقه؛ خروجی Excel/PDF هم‌زمان یا در پس‌زمینه (`/api/reports/jobs`).
- منوی «داشبورد مدیرعامل»: KPIها، نقدینگی، چک‌ها، عملکرد کارکنان، مقایسه و تجمیع شرکت‌های هلدینگ، تطبیق با دفتر کل؛ هر کارت به گزارش/دفتر کل وصل است. نیازمند `data.all`.
- PDF فارسی: بسته‌های `reportlab`، `arabic-reshaper`، `python-bidi` و یک فونت TTF (Dockerfile `fonts-dejavu-core` نصب می‌کند؛ برای Vazirmatn مسیر را در `PDF_FONT_PATH` بدهید). مایگریشن `0008`.

## اعلان، جستجو و فایل (مرحله ۱۵)
- **اعلان**: درون‌برنامه همیشه فعال؛ ایمیل/پیامک/Web Push اختیاری و پیش‌فرض خاموش (تنظیم هر کاربر: `/api/notifications/preferences`). رویدادها: کمبود موجودی، سررسید چک، سفارش جدید، تأیید فاکتور، تحویل موفق، ماموریت جدید. صف ارسال `NotificationDelivery` با تلاش مجدد؛ هشدارهای دوره‌ای با `dedupe_key` تکراری نمی‌شوند.
- **متغیرهای محیطی**: `SMTP_HOST/PORT/USER/PASSWORD/FROM`، `SMS_PROVIDER` + `SMS_WEBHOOK_URL/TOKEN` (درگاه با `register_sms_gateway` قابل افزودن)، `VAPID_PUBLIC_KEY/VAPID_PRIVATE_KEY/VAPID_SUBJECT` (+ `pywebpush`)، `CLAMAV_HOST/PORT` (آنتی‌ویروس اختیاری، پروتکل INSTREAM).
- **جستجو**: `/api/search/global`، `/api/search/advanced` (فقط فیلدها/عملگرهای لیست‌سفید)، فیلترهای ذخیره‌شده؛ روی PostgreSQL با ایندکس `pg_trgm`.
- **فایل**: تشخیص MIME از محتوا، سقف حجم، نام تصادفی روی دیسک، دانلود فقط با احراز هویت و دسترسی به رکورد مادر (+ `restricted`)، نسخه‌بندی و تاریخچه، حذف نرم.
- صفحه‌ها: «اعلان‌ها»، «جستجوی پیشرفته»، «اسناد و پیوست‌ها».

## کاربر اولیه
`admin` با رمز مقدار `ADMIN_PASSWORD`. در Production حتماً تغییر داده شود.

## تست
```bash
pip install -r requirements.txt
pytest -q
```

این نسخه هسته اجرایی و API مرکزی سیستم است؛ توسعه بعدی باید روی همین مدل داده و API انجام شود، نه با ایجاد دیتابیس جدا برای اپ‌ها.
