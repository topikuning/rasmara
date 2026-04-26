#!/usr/bin/env bash
# Bootstrap aplikasi RASMARA setelah Docker terpasang.
#   - cek .env.prod
#   - siapkan folder data
#   - build images
#   - migrate DB
#   - seed data
#   - create superadmin
#   - up semua service
set -euo pipefail

REPO_DIR="/opt/rasmara/app"
DATA_DIR="/opt/rasmara/data"
ENVF=".env.prod"

cd "$REPO_DIR"

if [[ ! -f "$ENVF" ]]; then
  echo "[ERROR] $REPO_DIR/$ENVF belum ada. Jalankan dulu:"
  echo "    cp .env.example .env.prod"
  echo "    nano .env.prod"
  exit 1
fi

echo "[1/7] siapkan folder data..."
sudo mkdir -p \
  "$DATA_DIR/postgres" \
  "$DATA_DIR/minio" \
  "$DATA_DIR/backend-static" \
  "$DATA_DIR/backend-media" \
  "$DATA_DIR/caddy" \
  "$DATA_DIR/caddy-config" \
  "/opt/rasmara/backups"
sudo chown -R "$USER:$USER" "$DATA_DIR" "/opt/rasmara/backups"

echo "[2/7] cek konfigurasi mode akses..."
SITE_ADDR=$(grep -E '^SITE_ADDRESS=' "$ENVF" | sed 's/^SITE_ADDRESS=//' || echo ":80")
DOMAIN=$(grep -E '^DOMAIN=' "$ENVF" | sed 's/^DOMAIN=//' || echo "")
echo "    SITE_ADDRESS=$SITE_ADDR  DOMAIN=$DOMAIN"

echo "[3/7] build images (dapat memakan waktu beberapa menit)..."
docker compose -f docker-compose.prod.yml --env-file "$ENVF" build

echo "[4/7] start postgres+redis+minio dulu..."
docker compose -f docker-compose.prod.yml --env-file "$ENVF" up -d postgres redis minio
echo "    tunggu postgres ready..."
for i in {1..30}; do
  if docker compose -f docker-compose.prod.yml --env-file "$ENVF" exec -T postgres pg_isready -U "$(grep -E '^POSTGRES_USER=' "$ENVF" | cut -d= -f2)" >/dev/null 2>&1; then
    echo "    postgres ready."
    break
  fi
  sleep 2
done

echo "[5/7] makemigrations + migrate..."
docker compose -f docker-compose.prod.yml --env-file "$ENVF" run --rm backend \
  bash -c "python manage.py makemigrations && python manage.py migrate --noinput"

echo "[5.1] collectstatic..."
docker compose -f docker-compose.prod.yml --env-file "$ENVF" run --rm backend \
  python manage.py collectstatic --noinput

echo "[5.2] seed_initial_data (permission, role, menu)..."
docker compose -f docker-compose.prod.yml --env-file "$ENVF" run --rm backend \
  python manage.py seed_initial_data

echo "[5.3] create_superadmin..."
docker compose -f docker-compose.prod.yml --env-file "$ENVF" run --rm backend \
  python manage.py create_superadmin

echo "[5.4] inisialisasi bucket MinIO..."
docker compose -f docker-compose.prod.yml --env-file "$ENVF" up -d minio-init || true

echo "[6/7] start semua service..."
docker compose -f docker-compose.prod.yml --env-file "$ENVF" up -d

echo "[6.1] tunggu Caddy & frontend siap..."
sleep 10

echo "[7/7] cek health backend..."
for i in {1..30}; do
  if curl -fsS http://localhost/api/v1/health/ >/dev/null 2>&1; then
    echo "    backend OK."
    break
  fi
  sleep 2
done

echo ""
echo "============================================================"
echo "[OK] RASMARA UP."
if [[ -n "$DOMAIN" && "$SITE_ADDR" == "https://"* ]]; then
  echo "Akses: https://$DOMAIN"
else
  IP=$(hostname -I | awk '{print $1}')
  echo "Akses: http://${IP}     (mode IP / port 80, HTTP)"
  echo ""
  echo "Setelah punya domain & DNS arahkan ke ${IP}, edit $ENVF:"
  echo "    DOMAIN=your-domain.tld"
  echo "    SITE_ADDRESS=https://your-domain.tld"
  echo "lalu: docker compose -f docker-compose.prod.yml --env-file $ENVF up -d --no-deps caddy"
fi
echo "============================================================"
