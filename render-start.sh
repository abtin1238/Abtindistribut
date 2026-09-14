#!/bin/sh
set -eu

: "${PORT:=10000}"
: "${DJANGO_SECRET_KEY:=abtin-demo-render-secret-key-change-this-in-production-2026}"
: "${ALLOWED_HOSTS:=${RENDER_EXTERNAL_HOSTNAME:-localhost}}"
: "${SEED_DEFAULT_PASSWORD:=Demo-Strong-Password-2026!}"
export PORT DJANGO_SECRET_KEY ALLOWED_HOSTS SEED_DEFAULT_PASSWORD

exec /usr/bin/supervisord -c /app/deploy/render-supervisord.conf
