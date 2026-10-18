# RUNBOOK — استقرار، بازیابی، رفع اشکال

## ۱) استقرار روی سرور تمیز (Ubuntu + Docker)
```sh
git clone <repo> abtin && cd abtin
cp .env.production.example .env
sh scripts/gen-secrets.sh >> .env      # DB_PASSWORD / ADMIN_PASSWORD / METRICS_TOKEN
nano .env                               # DOMAIN=erp.شما.com  (DNS باید به سرور اشاره کند؛ پورت ۸۰ و ۴۴۳ باز)
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps        # همه healthy
curl -fsS https://$DOMAIN/ready
```
ورود اول: کاربر `admin` با `ADMIN_PASSWORD` فایل `.env`. بعد از ورود رمز را از داخل سیستم عوض کنید.
> ⚠️ این compose در محیط ساخت اجرا **نشد** (Docker daemon در دسترس نبود)؛ اولین استقرار را روی سرور آزمایشی انجام دهید.

## ۲) آپدیت بدون downtime طولانی
```sh
git pull && docker compose -f docker-compose.prod.yml up -d --build app
docker compose -f docker-compose.prod.yml exec app alembic upgrade head
```
قبل از migration حتماً بکاپ دستی: `docker compose -f docker-compose.prod.yml exec backup sh -c 'pg_dump -Fc -f /backups/abtin_manual_$(date +%s).dump'`

## ۳) Rollback
1. کد نسخه‌ی قبل را checkout و `up -d --build app`.
2. اگر migration تغییر ساختار داده: `alembic downgrade -1` (نسخه‌های ۰۰۰۱–۰۰۱۱ در `docs/MIGRATIONS.md`) یا بازیابی از بکاپ (بخش ۴).

## ۴) بکاپ و بازیابی
- سرویس `backup` هر روز ساعت `BACKUP_HOUR_UTC` یک dump فشرده در volume `backups` می‌گیرد و فایل‌های قدیمی‌تر از `BACKUP_KEEP_DAYS` را پاک می‌کند.
- **خارج از سرور:** volume روی همین ماشین است. یک cron روی میزبان اضافه کنید، مثلاً  
  `rclone copy $(docker volume inspect abtin_backups -f '{{.Mountpoint}}') remote:abtin-backups --max-age 48h`.
- **آپلودها** (`uploads` volume) هم باید بکاپ شوند (فایل‌های لوگو/پیوست‌ها داخل دیتابیس نیستند).
- **تست بازیابی (حداقل ماهی یک‌بار):**  
  `docker compose -f docker-compose.prod.yml exec backup sh /scripts/restore-test.sh`  
  (روی PostgreSQL محلی تست شد: dump → دیتابیس موقت → شمارش جدول‌ها → حذف دیتابیس موقت).
- **بازیابی واقعی:** `docker compose ... stop app` ← `dropdb/createdb abtin_distribution` ← `pg_restore --no-owner -d abtin_distribution فایل.dump` ← `start app`.

## ۵) پایش
- `/health` زنده‌بودن، `/ready` اتصال دیتابیس (healthcheck داکر از `/ready` استفاده می‌کند).
- `/metrics` (Bearer `METRICS_TOKEN`): `abtin_http_requests_total{method,path,status_class}`، هیستوگرام تأخیر، uptime. در Prometheus از داخل شبکه‌ی internal اسکرپ کنید (از اینترنت توسط Caddy بسته است). هشدار پیشنهادی: نرخ `status_class="5xx"` > ۱٪ برای ۵ دقیقه؛ p95 تأخیر > ۲ ثانیه.
- لاگ: `docker compose -f docker-compose.prod.yml logs -f app` (هر پاسخ `X-Request-ID` دارد؛ همان شناسه در بدنه‌ی خطا است — برای ردیابی از کاربر بخواهید).
- Sentry/OpenTelemetry و داشبورد Grafana پیاده‌سازی **نشده‌اند**.

## ۶) رفع اشکال رایج
| علامت | علت محتمل | اقدام |
|---|---|---|
| app بالا نمی‌آید: `ADMIN_PASSWORD ضعیف` | رمز placeholder/کوتاه | `sh scripts/gen-secrets.sh` |
| `429 rate_limited` برای همه‌ی کاربران | پشت پروکسی همه از یک IP دیده می‌شوند | `TRUST_PROXY=1` (در compose.prod تنظیم است) |
| گواهی HTTPS صادر نمی‌شود | DNS یا پورت ۸۰ بسته | `docker compose logs proxy` |
| `/ready` خطا | دیتابیس بالا نیست/رمز اشتباه | `docker compose logs db`؛ `DB_PASSWORD` با حجم قدیمی pgdata ناسازگار است (رمز فقط در اولین ساخت volume اعمال می‌شود) |
| قفل شدن کاربر | ۵ ورود ناموفق | ۱۵ دقیقه صبر یا بازنشانی توسط مدیر |
