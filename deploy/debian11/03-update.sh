#!/usr/bin/env bash
# Update aplikasi RASMARA ke versi terbaru.
# Aman dipanggil berulang. Akan: pull, build, migrate, restart service yang berubah.
set -euo pipefail

REPO_DIR="/opt/rasmara/app"
ENVF=".env.prod"

cd "$REPO_DIR"

echo "[1/5] git pull..."
git fetch origin
git pull --ff-only

echo "[2/5] build images..."
docker compose -f docker-compose.prod.yml --env-file "$ENVF" build

echo "[3/5] migrate..."
docker compose -f docker-compose.prod.yml --env-file "$ENVF" run --rm backend \
  bash -c "python manage.py makemigrations && python manage.py migrate --noinput"

echo "[3.1] collectstatic..."
docker compose -f docker-compose.prod.yml --env-file "$ENVF" run --rm backend \
  python manage.py collectstatic --noinput

echo "[3.2] re-seed initial data (idempotent, mungkin permission baru)..."
docker compose -f docker-compose.prod.yml --env-file "$ENVF" run --rm backend \
  python manage.py seed_initial_data || true

echo "[4/5] restart service yang relevan..."
docker compose -f docker-compose.prod.yml --env-file "$ENVF" up -d \
  --no-deps backend frontend celery-worker celery-beat caddy

echo "[5/5] cek health..."
sleep 5
curl -fsS http://localhost/api/v1/health/ && echo " OK" || echo " WARN: health check gagal"

echo ""
echo "[DONE] Update selesai."
