# راهنمای API (v1)

مستندات تعاملی: `/docs` — مشخصات OpenAPI: `/api/v1/openapi.json` (با `API_DOCS_ENABLED=0` در production غیرفعال می‌شود).

## قراردادها
| موضوع | قرارداد |
|---|---|
| نسخه | همه‌ی مسیرها زیر `/api/v1`. مسیر بدون نسخه (`/api/...`) معادل v1 است و برای وب/موبایل فعلی می‌ماند. هدر پاسخ `X-API-Version: 1`. تغییر ناسازگار ⇒ `/api/v2`. |
| احراز هویت | `Authorization: Bearer <token>` (از `POST /auth/login`) **یا** کلید API: `X-API-Key: abk_…` (یا `Authorization: Bearer abk_…`). |
| دسترسی | هر مسیر Permission صریح دارد؛ کلید API همان دسترسی‌های نقشش را دارد (نه بیشتر از سازنده). |
| خطا | `{ "code", "message", "details", "request_id", "detail" }` — `detail` فقط برای سازگاری با کلاینت‌های قبلی است. |
| ردیابی | هر پاسخ `X-Request-ID` دارد؛ اگر کلاینت هدر `X-Request-ID` (۸–۶۴ نویسه‌ی `A-Za-z0-9._-`) بفرستد همان استفاده می‌شود. |
| صفحه‌بندی | `?limit=&offset=` (پیش‌فرض ۵۰۰، حداکثر ۱۰۰۰) + هدرهای `X-Total-Count`، `X-Limit`، `X-Offset`؛ بدنه همان آرایه است. فعلاً روی: `customers products suppliers purchases payments checks orders` و تحویل‌های وبهوک. سایر لیست‌ها فیلتر اختصاصی خودشان را دارند (مثلاً `invoices?status=&q=&start=&end=`). |
| Rate limit | پنجره‌ی ۶۰ثانیه‌ای به‌ازای هر توکن/کلید (یا IP). هدرها: `X-RateLimit-Limit/Remaining/Reset`. عبور ⇒ `429` + `Retry-After`. ورود: جداگانه به‌ازای IP. |
| Idempotency | `Idempotency-Key: <۸–۱۲۰ نویسه>` روی POST/PUT/PATCH/DELETE. تکرار با همان کلید و همان درخواست ⇒ همان پاسخ + `Idempotency-Replayed: true`. همان کلید با درخواست متفاوت ⇒ `422 idempotency_key_reuse`. همزمان ⇒ `409 idempotency_in_progress`. پاسخ‌های ۵xx/۴۰۱/۴۰۳/۴۲۹ ذخیره نمی‌شوند (قابل تلاش مجدد). نگهداری ۴۸ ساعت؛ دامنه‌ی کلید = توکن/کلید API فرستنده. |
| CORS | فقط originهای فهرست‌شده در `CORS_ORIGINS`؛ پیش‌فرض: بسته. |

### کدهای خطا
`bad_request 400` · `unauthorized 401` · `forbidden 403` · `not_found 404` · `conflict 409` · `validation_error 422` (در `details`: `[{field,message,type}]`) · `rate_limited 429` · `idempotency_key_reuse 422` · `idempotency_in_progress 409` · `invalid_idempotency_key 400` · `internal_error 500` (پیام شامل `request_id`).

## کلید API
- `POST /api-keys {name, role_id, expires_in_days?}` ⇒ کلید کامل **فقط همین یک‌بار** برمی‌گردد (فقط هش SHA-256 ذخیره می‌شود). نقش کلید نباید از دسترسی سازنده بیشتر باشد.
- `GET /api-keys` (بدون راز) · `DELETE /api-keys/{id}` (ابطال؛ فوری اثر می‌کند).
- مدیریت کلید/وبهوک با خود کلید API ممکن نیست (`403`). عملیات با کلید به نام کاربر سازنده‌ی کلید در Audit ثبت می‌شود و Data Scope هم از همان کاربر می‌آید.

## وبهوک خروجی
- `POST /webhooks {url, events[]}` (`events: ["*"]` = همه) ⇒ `secret` فقط یک‌بار. `GET/PATCH/DELETE /webhooks…`، `POST /webhooks/{id}/rotate-secret`، `POST /webhooks/{id}/test`، `GET /webhooks/{id}/deliveries`، `POST /webhook-deliveries/{id}/redeliver`، `GET /webhooks/events`.
- رویدادها: `order.created invoice.approved delivery.created delivery.delivered delivery.failed stock.low check.due task.assigned task.reminder lead.followup system.notice` (از همان نقطه‌ای می‌آیند که اعلان‌های درون‌برنامه ساخته می‌شوند).
- بدنه: `{"id","event","created_at","data":{title,body,entity,entity_id}}` (`id` برای حذف تکراری‌ها در گیرنده).
- هدرها: `X-Abtin-Event`، `X-Abtin-Event-Id`، `X-Abtin-Delivery`، `X-Abtin-Timestamp`، `X-Abtin-Signature: v1=<hex>`.
- **اعتبارسنجی امضا:** `hex(HMAC_SHA256(secret, f"{timestamp}.{raw_body}"))` را با `v1` مقایسه (constant-time) و `|now − timestamp| ≤ ۵ دقیقه` را بررسی کنید.
- پاسخ ۲xx = موفق. در غیر این صورت تلاش مجدد پس از ۱ دقیقه، ۵ دقیقه، ۳۰ دقیقه، ۲ ساعت، ۱۲ ساعت؛ بعد از تلاش ششم `failed`. ۳۰ شکست متوالی ⇒ اندپوینت غیرفعال می‌شود (با `PATCH active=true` فعال می‌شود). ریدایرکت دنبال نمی‌شود، timeout = ۸ ثانیه.
- **SSRF:** فقط `https` و مقصد باید آدرس عمومی باشد (loopback/خصوصی/link-local رد می‌شود).
- ارسال‌ها در حلقه‌ی پس‌زمینه‌ی `REMINDER_INTERVAL_SECONDS` (پیش‌فرض ۹۰۰ ثانیه) انجام می‌شود ⇒ تأخیر تحویل تا همان بازه ممکن است؛ برای تحویل سریع‌تر مقدار را کم کنید یا به Celery/ARQ منتقل کنید.

## Sync آفلاین (`POST /sync`)
بدنه: `{"events":[{"id","type","ref?","entity_id?","payload"}]}` (حداکثر ۲۰۰). `id` یکتای سمت کلاینت است؛ تکرار ⇒ `duplicate` (بدون اجرای دوباره).
نتیجه‌ی هر رویداد: `applied` | `duplicate` | `retry` (وابستگی هنوز نرسیده/خطای موقت؛ کلاینت نگه دارد) | `rejected` (+`detail`؛ اگر `code:"conflict"` یعنی با وضعیت فعلی سرور تعارض دارد، مثلاً ویزیت/وظیفه/تحویل قبلاً بسته شده). `GET /sync/events?status=` تاریخچه‌ی رویدادهای خود کاربر.
نوع‌ها: `visit.start visit.finish order.create payment.create lead.create lead.activity task.create task.done delivery.loaded delivery.start delivery.delivered delivery.failed delivery.collect gps.points`. هر نوع همان Permission مسیر معادلش را می‌خواهد.
سیاست تعارض (فعلی): **سرور برنده است**؛ رویداد متعارض رد و به کلاینت گزارش می‌شود، نه ادغام خودکار.

## سلامت
`GET /health` و `GET /ready` (بررسی دیتابیس؛ ۵۰۳ اگر در دسترس نباشد) — بدون احراز هویت و بدون rate limit.


## نشست و refresh (مرحله ۱ امنیت)
- `POST /api/auth/login` → `{token, expires_in, company_id}` + کوکی HttpOnly `abtin_rt`.
- `POST /api/auth/refresh` (هدر `X-Requested-With: abtin`، بدون Authorization) → توکن تازه؛ کوکی چرخانده می‌شود. ۴۰۱ یعنی دوباره وارد شوید.
- `POST /api/users/{id}/reset-password` `{new_password}` (مجوز `admin.write`).

- `POST /api/purchases/{id}/receive` (بدنهٔ اختیاری `items` برای رسید جزئی)، `POST /api/purchases/{id}/cancel`، `POST /api/purchases/{id}/allocate-cost`.
- `GET /api/customers/{id}`، `/api/customers/{id}/addresses` و `/contacts` (GET/POST/PATCH/DELETE).
- `GET /api/payroll/runs/{rid}/payslip/{eid}/pdf`، `GET/POST/PATCH /api/shifts`، `PUT /api/employees/{id}/shift`، `GET /api/attendance/report?period=`.
- `GET/POST/PATCH/DELETE /api/geofences`، `GET /api/geofences/events`.
