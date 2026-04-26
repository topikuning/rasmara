#!/usr/bin/env bash
# Restore RASMARA dari backup.
# Pemakaian:
#   bash restore.sh /path/to/db_20260426_020000.sql.gz
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Pemakaian: $0 <path/to/db_*.sql.gz>" >&2
  exit 1
fi

DUMP="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
ENVF="${ENVF:-.env.prod}"

cd "$REPO_DIR"

PG_USER=$(grep -E '^POSTGRES_USER=' "$ENVF" | cut -d= -f2)
PG_DB=$(grep -E '^POSTGRES_DB=' "$ENVF" | cut -d= -f2)

DC="docker compose -f docker-compose.prod.yml --env-file $ENVF"

echo "[!] PERHATIAN: ini akan DROP & RECREATE database '$PG_DB'."
read -rp "Lanjut restore dari $DUMP? [y/N] " ans
[[ "${ans,,}" == "y" ]] || exit 1

echo "[1/3] stop aplikasi (postgres tetap up)..."
$DC stop backend frontend celery-worker celery-beat 2>/dev/null || true

echo "[2/3] drop & recreate DB..."
$DC exec -T postgres psql -U "$PG_USER" -d postgres -c "DROP DATABASE IF EXISTS $PG_DB;"
$DC exec -T postgres psql -U "$PG_USER" -d postgres -c "CREATE DATABASE $PG_DB;"

echo "[2.1] load dump..."
gunzip -c "$DUMP" | $DC exec -T postgres psql -U "$PG_USER" -d "$PG_DB"

echo "[3/3] start aplikasi..."
$DC up -d

echo "[OK] Restore selesai."
