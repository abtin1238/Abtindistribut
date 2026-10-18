#!/bin/sh
# هر روز ساعت BACKUP_HOUR_UTC یک dump فشرده می‌گیرد و فایل‌های قدیمی‌تر از BACKUP_KEEP_DAYS را پاک می‌کند.
# مهم: /backups هم روی همین سرور است؛ حتماً با rclone/rsync/S3 یک نسخه را خارج از سرور نگه دارید (docs/RUNBOOK.md).
set -eu
HOUR="${BACKUP_HOUR_UTC:-0}"; KEEP="${BACKUP_KEEP_DAYS:-14}"
do_backup() {
  f="/backups/abtin_$(date -u +%Y%m%d_%H%M%S).dump"
  pg_dump --format=custom --no-owner --file="$f.tmp" && mv "$f.tmp" "$f" && echo "[backup] ok $f ($(du -h "$f" | cut -f1))"
  find /backups -name 'abtin_*.dump' -mtime +"$KEEP" -delete
}
last=""
while true; do
  now_day="$(date -u +%Y%m%d)"; now_hour="$(date -u +%H | sed 's/^0//')"; now_hour="${now_hour:-0}"
  if [ "$now_day" != "$last" ] && [ "$now_hour" -ge "$HOUR" ]; then
    if do_backup; then last="$now_day"; else echo "[backup] FAILED" >&2; fi
  fi
  sleep 300
done
