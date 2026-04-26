#!/usr/bin/env bash
# Update aplikasi RASMARA ke versi terbaru.
# Path repo di-derive dari lokasi script.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
ENVF="${ENVF:-.env.prod}"
PROFILES="${PROFILES:-}"

cd "$REPO_DIR"

DC="docker compose -f docker-compose.prod.yml $PROFILES --env-file $ENVF"

echo "[*] Repo: $REPO_DIR"
echo "[1/5] git pull..."
git fetch origin
git pull --ff-only

echo "[2/5] build images..."
$DC build

echo "[3/5] migrate..."
$DC run --rm backend \
  bash -c "python manage.py makemigrations && python manage.py migrate --noinput"

echo "[3.1] collectstatic..."
$DC run --rm backend python manage.py collectstatic --noinput

echo "[3.2] re-seed initial data (idempotent)..."
$DC run --rm backend python manage.py seed_initial_data || true

echo "[4/5] restart service yang relevan..."
$DC up -d --no-deps backend frontend caddy
if [[ "$PROFILES" == *"queue"* ]]; then
  $DC up -d --no-deps celery-worker celery-beat
fi

echo "[5/5] cek health..."
sleep 5
curl -fsS http://localhost/api/v1/health/ && echo " OK" || echo " WARN: health check gagal"

echo ""
echo "[DONE] Update selesai."
