#!/usr/bin/env bash
# Bootstrap aplikasi RASMARA setelah Docker terpasang.
#   - cek .env.prod
#   - siapkan folder data
#   - build images (1 image utk backend, 1 utk frontend)
#   - migrate DB
#   - seed data
#   - create superadmin
#   - up service utama (postgres + backend + frontend + caddy)
#
# Catatan VPS kecil (1 vCPU + 2GB RAM):
# Stack default tidak menjalankan Redis, Celery, MinIO. Aktifkan saat
# diperlukan dengan PROFILES env (mis. PROFILES="--profile queue").
set -euo pipefail

REPO_DIR="/opt/rasmara/app"
DATA_DIR="/opt/rasmara/data"
ENVF=".env.prod"
PROFILES="${PROFILES:-}"     # contoh: PROFILES="--profile queue --profile s3"

cd "$REPO_DIR"

if [[ ! -f "$ENVF" ]]; then
  echo "[ERROR] $REPO_DIR/$ENVF belum ada. Jalankan dulu:"
  echo "    cp .env.example .env.prod"
  echo "    nano .env.prod"
  exit 1
fi

# Cek RAM & swap — peringatan untuk VPS sangat kecil
TOTAL_MEM_MB=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
SWAP_MB=$(awk '/SwapTotal/ {print int($2/1024)}' /proc/meminfo)
echo "[*] RAM total: ${TOTAL_MEM_MB} MB | Swap: ${SWAP_MB} MB"
if [[ $TOTAL_MEM_MB -lt 1800 ]]; then
  echo "[WARN] RAM <2GB. Pastikan swap aktif minimal 4GB."
  if [[ $SWAP_MB -lt 2000 ]]; then
    echo "[WARN] Swap kecil. Build mungkin OOM. Jalankan 00-prerequisites.sh dulu."
  fi
fi

DC="docker compose -f docker-compose.prod.yml $PROFILES --env-file $ENVF"

echo "[1/7] siapkan folder data..."
sudo mkdir -p \
  "$DATA_DIR/postgres" \
  "$DATA_DIR/backend-static" \
  "$DATA_DIR/backend-media" \
  "$DATA_DIR/caddy" \
  "$DATA_DIR/caddy-config" \
  "/opt/rasmara/backups"
# MinIO data folder hanya bila profile s3 aktif
if [[ "$PROFILES" == *"s3"* ]]; then
  sudo mkdir -p "$DATA_DIR/minio"
fi
sudo chown -R "$USER:$USER" "$DATA_DIR" "/opt/rasmara/backups"

echo "[2/7] cek konfigurasi mode akses..."
SITE_ADDR=$(grep -E '^SITE_ADDRESS=' "$ENVF" | sed 's/^SITE_ADDRESS=//' || echo ":80")
DOMAIN=$(grep -E '^DOMAIN=' "$ENVF" | sed 's/^DOMAIN=//' || echo "")
echo "    SITE_ADDRESS=$SITE_ADDR  DOMAIN=$DOMAIN"
echo "    Profiles: ${PROFILES:-(default = postgres+backend+frontend+caddy)}"

echo "[3/7] build images (lambat di pertama kali — ~5-10 menit)..."
$DC build

echo "[4/7] start postgres dulu..."
$DC up -d postgres
echo "    tunggu postgres ready..."
for i in {1..30}; do
  if $DC exec -T postgres pg_isready -U "$(grep -E '^POSTGRES_USER=' "$ENVF" | cut -d= -f2)" >/dev/null 2>&1; then
    echo "    postgres ready."
    break
  fi
  sleep 2
done

echo "[5/7] makemigrations + migrate..."
$DC run --rm backend \
  bash -c "python manage.py makemigrations && python manage.py migrate --noinput"

echo "[5.1] collectstatic..."
$DC run --rm backend python manage.py collectstatic --noinput

echo "[5.2] seed_initial_data (permission, role, menu)..."
$DC run --rm backend python manage.py seed_initial_data

echo "[5.3] create_superadmin..."
$DC run --rm backend python manage.py create_superadmin

if [[ "$PROFILES" == *"s3"* ]]; then
  echo "[5.4] inisialisasi bucket MinIO..."
  $DC up -d minio-init || true
fi

echo "[6/7] start semua service (sesuai profil)..."
$DC up -d

echo "[6.1] tunggu Caddy & frontend siap (10 detik)..."
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
echo ""
echo "RAM idle stack (perkiraan): postgres ~150MB + backend ~250MB + frontend ~150MB"
echo "                            + caddy ~20MB = ~570MB total."
echo ""
echo "Untuk modul yang butuh queue (notifikasi/scheduler):"
echo "  PROFILES='--profile queue' bash deploy/debian11/02-app-bootstrap.sh"
echo "  atau:"
echo "  docker compose -f docker-compose.prod.yml --profile queue --env-file $ENVF up -d"
echo "============================================================"
