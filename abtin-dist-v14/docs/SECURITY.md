# امنیت — چک‌لیست و ریسک‌های پذیرفته‌شده

## انجام‌شده
- JWT با انقضا، قفل حساب پس از تلاش ناموفق، Rate limit (ورود و عمومی)، Idempotency-Key، کلید API هش‌شده با انقضا/ابطال.
- Permission سراسری + Data Scope + جداسازی tenant (تست‌ها نوشته شده، اجرا نشده).
- هدرها: CSP، X-Frame-Options، nosniff، Referrer-Policy، Permissions-Policy، **HSTS (فقط روی HTTPS)**، `Cache-Control: no-store` برای `/api/*`.
- رمز ادمین: placeholder/ضعیف رد می‌شود؛ `APP_ENV=production` ⇒ حداقل ۱۲ نویسه وگرنه راه‌اندازی متوقف می‌شود.
- آپلود: تشخیص نوع با magic bytes، سقف حجم، دانلود فقط با احراز هویت.
- وبهوک: امضا + محافظ SSRF. `/metrics` فقط با `METRICS_TOKEN` و در Caddy از اینترنت بسته است.
- شبکه: دیتابیس فقط در شبکه‌ی internal دوکر؛ فقط Caddy پورت ۸۰/۴۴۳ دارد؛ کانتینر app غیر‌root.
- CI: `pip-audit`، بررسی نحو JS/sh. (`npm audit` لازم نیست؛ فرانت وابستگی npm ندارد.)

## مرحله ۱ امنیت (اکتبر ۲۰۲۶)
- **Refresh token چرخشی:** ورود یک access token کوتاه‌عمر (`ACCESS_TOKEN_MINUTES`، پیش‌فرض ۶۰) در بدنه و یک refresh token در کوکی `abtin_rt` (HttpOnly، `SameSite=Strict`، `Secure` روی HTTPS، `Path=/api`، `REFRESH_TOKEN_DAYS` پیش‌فرض ۱۴) می‌دهد. `POST /api/auth/refresh` (با هدر `X-Requested-With: abtin`) توکن را می‌چرخاند؛ فقط هش SHA-256 در جدول `refresh_tokens` ذخیره می‌شود.
- **تشخیص سرقت:** استفاده‌ی مجدد از refresh باطل‌شده (بیش از `REFRESH_REUSE_GRACE_SECONDS`=۲۰ ثانیه، برای رقابت چندتب) کل خانواده‌ی ورود را می‌بندد و در Audit ثبت می‌شود.
- logout، logout-all، تغییر رمز، بازنشانی رمز، غیرفعال‌سازی کاربر، تعویض شرکت: refreshهای مربوط را باطل می‌کنند.
- `POST /api/users/{id}/reset-password` (مدیر): سیاست رمز + ابطال همه‌ی نشست‌ها؛ سیاست رمز هنگام ساخت کاربر هم اعمال می‌شود.
- کلاینت‌ها: `web/js/auth-refresh.js` روی `fetch` نصب می‌شود (وب، فاکتور، دو PWA)؛ در ۴۰۱ یک‌بار تمدید و درخواست را تکرار می‌کند.
- Rate limit جدا برای refresh (`RATE_LIMIT_REFRESH_PER_MIN`).
- ⚠️ همه‌ی این‌ها با `tests/test_stage1_security.py` پوشش داده شده‌اند ولی **اجرا نشده‌اند** (محیط ساخت بدون pip).

### تکمیل مرحله ۱
- **Audit Log:** ستون‌های `ip` و `request_id` روی هر رکورد (از middleware با contextvar)؛ ORM هر `UPDATE/DELETE` روی Audit را رد می‌کند و در PostgreSQL تریگر `audit_logs_no_change` (مایگریشن `0019`) آن را در سطح دیتابیس می‌بندد. IP کلاینت فقط با `TRUST_PROXY=1` از `X-Forwarded-For` خوانده می‌شود (قبلاً در لاگ ورود بدون شرط خوانده می‌شد و جعل‌پذیر بود).
- **ماتریس دسترسی:** `tests/test_stage1_matrix.py` همه‌ی مسیرهای `/api/*` را از روی `app.routes` می‌شمارد: بدون توکن ۴۰۱، مسیر ناشناخته ⇒ `admin.write`، نقش «فروشنده» برای هر مسیر دقیقاً مطابق مجوزهایش ۲۰۰/۴۰۳ می‌گیرد، Audit تغییرناپذیر است. (⚠️ اجرا نشده.)

## ریسک‌های پذیرفته‌شده / باز
1. **access token هنوز در localStorage است** (اما فقط ۶۰ دقیقه اعتبار دارد و refresh دور از دسترس JS است). انتقال کامل به کوکی HttpOnly نیازمند CSRF token برای همه‌ی متدهای تغییر‌دهنده است.
2. `script-src 'unsafe-inline'`: صفحه‌ها هنوز handler درون‌خطی (`onclick=`) دارند؛ حذف آن‌ها برای CSP بدون `unsafe-inline` لازم است.
3. بررسی آنتی‌ویروس آپلود (ClamAV) اختیاری و پیاده‌سازی نشده.
4. تست نفوذ دستی (SQLi/IDOR/brute-force) اجرا نشد؛ ORM پارامتریک است و `text()` فقط برای `SELECT 1` و DDL ثابت است (grep).
5. `docs/` حاوی نسخه‌ی Swagger از CDN است؛ در production `API_DOCS_ENABLED=0` (پیش‌فرض compose).
