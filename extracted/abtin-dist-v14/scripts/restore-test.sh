#!/bin/sh
# تست بازیابی: آخرین dump را در یک دیتابیس موقت بازیابی می‌کند و تعداد ردیف جدول‌های کلیدی را چاپ می‌کند.
# اجرا روی سرور:  docker compose -f docker-compose.prod.yml exec backup sh /scripts/restore-test.sh
set -eu
f="${1:-$(ls -1t /backups/abtin_*.dump 2>/dev/null | head -1)}"
[ -n "$f" ] && [ -f "$f" ] || { echo "هیچ بکاپی پیدا نشد" >&2; exit 1; }
T="restore_test_$$"
echo "[restore-test] file=$f db=$T"
createdb "$T"
trap 'dropdb --if-exists "$T"' EXIT
pg_restore --no-owner --dbname="$T" "$f"
for t in users companies customers products invoices journal_entries journal_lines stock_moves; do
  n="$(psql -At -d "$T" -c "SELECT count(*) FROM $t" 2>/dev/null || echo 'N/A')"
  echo "  $t: $n"
done
echo "[restore-test] OK"
