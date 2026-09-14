#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV="$ROOT/.venv"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3 is required."
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "Node.js/npm is required."
  exit 1
fi

if [ ! -d "$VENV" ]; then
  "$PYTHON_BIN" -m venv "$VENV"
fi
source "$VENV/bin/activate"
pip install -r backend/requirements.txt

cd backend
export DJANGO_SETTINGS_MODULE=config.settings.dev
export USE_SQLITE=1
python manage.py migrate --noinput
python manage.py seed_demo_data --password "${SEED_DEFAULT_PASSWORD:-Demo-Strong-Password-2026!}"
python manage.py collectstatic --noinput
cd ../frontend
npm install

cleanup() {
  kill 0 2>/dev/null || true
}
trap cleanup INT TERM EXIT

(cd "$ROOT/backend" && DJANGO_SETTINGS_MODULE=config.settings.dev USE_SQLITE=1 "$ROOT/.venv/bin/python" manage.py runserver 127.0.0.1:8000) &
(cd "$ROOT/frontend" && npm run dev -- --host 127.0.0.1 --port 3000) &
wait
