# استقرار روی Railway

۱. پروژه را روی GitHub بگذارید (یا با `railway up`). در Railway: **New Project → Deploy from GitHub repo**. فایل `railway.toml` و `Dockerfile` خودکار شناسایی می‌شوند.

۲. **دیتابیس:** در همان پروژه **+ New → Database → PostgreSQL**. سپس در سرویس اپ، Variable بسازید:
   `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`
   (آدرس `postgres://` خودکار به `postgresql+psycopg://` تبدیل می‌شود.)

۳. **متغیرهای سرویس اپ** (Variables):

| متغیر | مقدار |
|---|---|
| `APP_ENV` | `production` |
| `ADMIN_PASSWORD` | **تنظیم نکنید.** بار اول صفحهٔ «تعریف مدیر کل» باز می‌شود (فقط برای حالت قدیمی ادمین `admin`) |
| `SETUP_TOKEN` | توصیه می‌شود: یک کد دلخواه؛ بدون آن هر کسی که زودتر آدرس را باز کند می‌تواند مدیر کل را تعریف کند |
| `TRUST_PROXY` | `1` |
| `UPLOAD_DIR` | `/data/uploads` |
| `RAILWAY_RUN_UID` | `0` (تا اپ بتواند روی Volume بنویسد) |
| `METRICS_TOKEN` | اختیاری |

۴. **Volume (ماندگاری فایل‌ها):** در سرویس اپ **Settings → Volumes → Add Volume** با Mount Path = `/data`. بدون Volume فایل‌های آپلودشده با هر دیپلوی پاک می‌شوند.

۵. **دامنه:** Settings → Networking → **Generate Domain**. پورت را Railway با `PORT` می‌دهد و `run.sh` همان را می‌خواند.

۶. اولین باز کردن `/app/`: فرم **تعریف مدیر کل** (نام، نام کاربری، رمز، نام شرکت و در صورت تنظیم، `SETUP_TOKEN`) می‌آید. مدیر کل به شعبه وصل نیست و همهٔ شعبه‌ها زیر دست اوست. بعد از ساخته‌شدن اولین کاربر، این صفحه برای همیشه بسته می‌شود.

۷. بعد از دیپلوی: `https://<دامنه>/api/ready` باید `ok` بدهد. پنل React روی `/app/` و پنل قدیمی روی `/web/` است.

نکته‌ها:
- فقط **یک replica** نگه دارید (یادآوری‌ها و کارهای پس‌زمینه داخل خود اپ اجرا می‌شوند).
- جدول‌ها در اولین اجرا خودکار ساخته می‌شوند.
- پشتیبان‌گیری: از بخش Backups خود Postgres در Railway استفاده کنید (سرویس `backup` در docker-compose روی Railway لازم نیست).
