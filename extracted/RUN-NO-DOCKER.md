# اجرای آبتین بدون Docker

این روش برای اجرای کامل محیط توسعه روی Windows/macOS/Linux است و به Docker نیاز ندارد.

## پیش‌نیاز

- Python 3.11+
- Node.js 20+
- npm

## اجرا

در ریشه پروژه:

```bash
bash scripts/run-local.sh
```

اسکریپت به‌صورت خودکار:

1. محیط مجازی Python می‌سازد.
2. وابستگی‌های Backend را نصب می‌کند.
3. SQLite را برای اجرای محلی فعال می‌کند.
4. Migration را اجرا می‌کند.
5. داده و کاربران نمونه را Seed می‌کند.
6. Static files را جمع می‌کند.
7. وابستگی‌های Frontend را نصب می‌کند.
8. Backend و Frontend را همزمان اجرا می‌کند.

آدرس‌ها:

- Frontend: http://127.0.0.1:3000
- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/api/docs/

## کاربران نمونه

رمز همه کاربران Seed شده:

`Demo-Strong-Password-2026!`

کاربران اصلی:

- `admin`
- `company.manager`
- `sales.manager`
- `warehouse.manager`
- `warehouse.keeper`
- `sales.rep`
- `driver`
- `accountant`
- `finance.manager`
- `hr`
- `operator`
- `customer.aria`
- `system.admin`

برای توقف، `Ctrl+C` بزنید.

## اجرای Production

برای Production از PostgreSQL و Redis استفاده کنید و تنظیمات `config.settings.prod` و متغیرهای محیطی امنیتی پروژه را تنظیم کنید. اجرای SQLite برای توسعه و تست محلی است.
