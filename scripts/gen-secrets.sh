#!/bin/sh
# رمزهای تصادفی قوی چاپ می‌کند؛ خروجی را به .env اضافه کنید:  sh scripts/gen-secrets.sh >> .env
set -eu
rnd() { python3 -c 'import secrets;print(secrets.token_urlsafe(24))' 2>/dev/null || head -c 24 /dev/urandom | base64 | tr '+/' '-_' | tr -d '='; }
echo "DB_PASSWORD=$(rnd)"
echo "ADMIN_PASSWORD=$(rnd)"
echo "METRICS_TOKEN=$(rnd)"
