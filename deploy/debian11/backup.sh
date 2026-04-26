#!/usr/bin/env bash
# Backup harian RASMARA: dump PostgreSQL + tar MinIO data.
# Retention 14 hari. Path di-derive dari lokasi script.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
DATA_DIR="${DATA_DIR:-$REPO_DIR/data}"
BACKUP_DIR="${BACKUP_DIR:-$REPO_DIR/backups}"
ENVF="${ENVF:-.env.prod}"

cd "$REPO_DIR"
mkdir -p "$BACKUP_DIR"

TS=$(date +%Y%m%d_%H%M%S)
PG_USER=$(grep -E '^POSTGRES_USER=' "$ENVF" | cut -d= -f2)
PG_DB=$(grep -E '^POSTGRES_DB=' "$ENVF" | cut -d= -f2)

DC="docker compose -f docker-compose.prod.yml --env-file $ENVF"

echo "[*] Repo: $REPO_DIR"
echo "[1/3] PostgreSQL dump..."
$DC exec -T postgres \
  pg_dump -U "$PG_USER" "$PG_DB" | gzip > "$BACKUP_DIR/db_$TS.sql.gz"

echo "[2/3] MinIO data tar (jika ada)..."
if [[ -d "$DATA_DIR/minio" ]]; then
  tar -czf "$BACKUP_DIR/minio_$TS.tar.gz" -C "$DATA_DIR/minio" . || true
fi

# Backup folder media (filesystem storage default)
if [[ -d "$DATA_DIR/backend-media" ]]; then
  tar -czf "$BACKUP_DIR/media_$TS.tar.gz" -C "$DATA_DIR/backend-media" . || true
fi

echo "[3/3] retention (hapus > 14 hari)..."
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +14 -delete
find "$BACKUP_DIR" -name "minio_*.tar.gz" -mtime +14 -delete
find "$BACKUP_DIR" -name "media_*.tar.gz" -mtime +14 -delete

echo "[OK] Backup selesai: $BACKUP_DIR/db_$TS.sql.gz"
ls -lh "$BACKUP_DIR" | tail -n 10
