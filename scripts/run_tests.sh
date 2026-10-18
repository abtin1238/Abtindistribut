#!/usr/bin/env bash
# هر فایل تست در پروسهٔ جدا اجرا می‌شود: engine/DB در import ساخته می‌شود و فایل‌ها DATABASE_URL خودشان را می‌گذارند.
set -u
cd "$(dirname "$0")/.."
fail=0
# COV=1 ⇒ پوشش را بین پروسه‌ها جمع می‌کند (برای CI)؛ COV_MIN آستانهٔ شکست (پیش‌فرض: بدون آستانه)
COVARGS=""
if [ "${COV:-0}" = "1" ]; then COVARGS="--cov=app/services --cov=app/modules/sales --cov=app/modules/inventory --cov=app/modules/finance --cov-append"; rm -f .coverage; fi
for f in tests/test_*.py; do
  rm -f /tmp/abtin_dist_*.sqlite3 /tmp/abtin_*.sqlite3
  out=$(python3 -m pytest -q -p no:cacheprovider $COVARGS "$f" 2>&1); rc=$?
  if [ $rc -ne 0 ]; then echo "FAIL $f"; echo "$out" | grep -E "^(FAILED|E  )" | head -8; fail=1; fi
done
if [ "${COV:-0}" = "1" ]; then python3 -m coverage report --show-missing ${COV_MIN:+--fail-under=$COV_MIN} || fail=1; fi
[ $fail -eq 0 ] && echo "ALL GREEN"; exit $fail
