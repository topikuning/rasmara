#!/usr/bin/env bash
# Bootstrap aplikasi RASMARA setelah Docker terpasang.
# Path repo di-derive dari lokasi script ini, BUKAN hardcode.
#
# Pemakaian (dari mana saja):
#   bash deploy/debian11/02-app-bootstrap.sh
#   PROFILES='--profile queue' bash deploy/debian11/02-app-bootstrap.sh
#
# Variabel env yang bisa di-override:
#   REPO_DIR     (default: derive dari lokasi script)
#   DATA_DIR     (default: $REPO_DIR/data)
#   BACKUP_DIR   (default: $REPO_DIR/backups)
#   ENVF         (default: .env.prod, relative ke $REPO_DIR)
#   PROFILES     (default: kosong = stack default)
set -euo pipefail

# Derive REPO_DIR dari lokasi script ini.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
DATA_DIR="${DATA_DIR:-$REPO_DIR/data}"
BACKUP_DIR="${BACKUP_DIR:-$REPO_DIR/backups}"
ENVF="${ENVF:-.env.prod}"
PROFILES="${PROFILES:-}"

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
echo "[*] Repo dir: $REPO_DIR"
echo "[*] Data dir: $DATA_DIR"
echo "[*] Backup dir: $BACKUP_DIR"
echo "[*] RAM total: ${TOTAL_MEM_MB} MB | Swap: ${SWAP_MB} MB"
if [[ $TOTAL_MEM_MB -lt 1800 ]]; then
  echo "[WARN] RAM <2GB. Pastikan swap aktif minimal 4GB."
  if [[ $SWAP_MB -lt 2000 ]]; then
    echo "[WARN] Swap kecil. Build mungkin OOM. Jalankan 00-prerequisites.sh dulu."
  fi
fi

DC="docker compose -f docker-compose.prod.yml $PROFILES --env-file $ENVF"

echo "[1/7] siapkan folder data..."
mkdir -p \
  "$DATA_DIR/postgres" \
  "$DATA_DIR/backend-static" \
  "$DATA_DIR/backend-media" \
  "$DATA_DIR/caddy" \
  "$DATA_DIR/caddy-config" \
  "$BACKUP_DIR"
# MinIO data folder hanya bila profile s3 aktif
if [[ "$PROFILES" == *"s3"* ]]; then
  mkdir -p "$DATA_DIR/minio"
fi
# docker-compose pakai path relatif './data/...', jadi DATA_DIR HARUS = $REPO_DIR/data.
# Bila user override DATA_DIR ke path lain, peringatkan.
if [[ "$DATA_DIR" != "$REPO_DIR/data" ]]; then
  echo "[WARN] DATA_DIR ($DATA_DIR) berbeda dari $REPO_DIR/data."
  echo "       docker-compose pakai path relatif './data/...' — jika DATA_DIR di luar repo,"
  echo "       buat symlink: ln -s '$DATA_DIR' '$REPO_DIR/data'"
  if [[ ! -e "$REPO_DIR/data" ]]; then
    ln -s "$DATA_DIR" "$REPO_DIR/data"
    echo "       Symlink dibuat: $REPO_DIR/data -> $DATA_DIR"
  fi
fi

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
PG_USER=$(grep -E '^POSTGRES_USER=' "$ENVF" | cut -d= -f2)
for i in {1..30}; do
  if $DC exec -T postgres pg_isready -U "$PG_USER" >/dev/null 2>&1; then
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
  echo "lalu: $DC up -d --no-deps caddy"
fi
echo ""
echo "Untuk modul yang butuh queue (notifikasi/scheduler):"
echo "  PROFILES='--profile queue' bash $SCRIPT_DIR/02-app-bootstrap.sh"
echo "============================================================"
