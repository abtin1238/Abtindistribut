#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker is not installed. Install Docker Engine + Compose plugin first." >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: Docker Compose plugin is missing." >&2
  exit 1
fi
if [[ -e .env ]]; then
  echo "Found existing .env; will not overwrite it."
else
  cp .env.private.example .env
  chmod 600 .env
  DB_PASSWORD="$(openssl rand -hex 32)"
  ADMIN_PASSWORD="$(openssl rand -base64 24 | tr -d '\n')"
  METRICS_TOKEN="$(openssl rand -hex 32)"
  printf '\nDB_PASSWORD=%s\nADMIN_PASSWORD=%s\nMETRICS_TOKEN=%s\n' "$DB_PASSWORD" "$ADMIN_PASSWORD" "$METRICS_TOKEN" >> .env
  echo "Generated database/admin secrets in .env (permissions 600)."
fi

if ! grep -q '^TUNNEL_TOKEN=.' .env; then
  echo
  echo "Create a Cloudflare Tunnel in Zero Trust > Networks > Tunnels."
  echo "Configure its public hostname to your chosen hostname and service URL http://app:8000."
  echo "In the Cloudflare Access application, allow ONLY your exact email address."
  read -rsp "Paste the Cloudflare Tunnel token (input hidden): " TUNNEL_TOKEN
  echo
  if [[ -z "$TUNNEL_TOKEN" ]]; then echo "ERROR: tunnel token is required." >&2; exit 1; fi
  printf '\nTUNNEL_TOKEN=%s\n' "$TUNNEL_TOKEN" >> .env
  chmod 600 .env
fi

echo "Building and starting private application..."
docker compose -f docker-compose.private.yml up -d --build

echo
echo "Container status:"
docker compose -f docker-compose.private.yml ps

echo
echo "Recent app logs:"
docker compose -f docker-compose.private.yml logs --tail=80 app

echo
echo "IMPORTANT: In Cloudflare Access, verify only your email is in the Allow policy."
echo "Keep .env private. Admin login username is admin; use the generated ADMIN_PASSWORD in .env."
