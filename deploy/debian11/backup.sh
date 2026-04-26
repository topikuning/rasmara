#!/usr/bin/env bash
# Backup harian RASMARA: dump PostgreSQL + tar MinIO data.
# Retention 14 hari.
set -euo pipefail

REPO_DIR="/opt/rasmara/app"
DATA_DIR="/opt/rasmara/data"
BACKUP_DIR="/opt/rasmara/backups"
ENVF=".env.prod"

cd "$REPO_DIR"
mkdir -p "$BACKUP_DIR"

TS=$(date +%Y%m%d_%H%M%S)
PG_USER=$(grep -E '^POSTGRES_USER=' "$ENVF" | cut -d= -f2)
PG_DB=$(grep -E '^POSTGRES_DB=' "$ENVF" | cut -d= -f2)

echo "[1/3] PostgreSQL dump..."
docker compose -f docker-compose.prod.yml --env-file "$ENVF" exec -T postgres \
  pg_dump -U "$PG_USER" "$PG_DB" | gzip > "$BACKUP_DIR/db_$TS.sql.gz"

echo "[2/3] MinIO data tar..."
tar -czf "$BACKUP_DIR/minio_$TS.tar.gz" -C "$DATA_DIR/minio" . || true

echo "[3/3] retention (hapus > 14 hari)..."
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +14 -delete
find "$BACKUP_DIR" -name "minio_*.tar.gz" -mtime +14 -delete

echo "[OK] Backup selesai: $BACKUP_DIR/db_$TS.sql.gz"
ls -lh "$BACKUP_DIR" | tail -n 10
