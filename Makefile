SHELL := /bin/bash

# ============================================================
# RASMARA Makefile
# ============================================================
# KONVENSI:
#   DEV  (Docker Compose dev di laptop):
#       Compose file : docker-compose.yml
#       Env file     : .env
#       Target prefix: dev-* (atau bare: 'make up', 'make migrate', dst.)
#
#   PROD (VPS Debian 11):
#       Compose file : docker-compose.prod.yml
#       Env file     : .env.prod
#       Target prefix: prod-*
#
# Tiap target validasi file env-nya WAJIB ada sebelum jalan.
# ============================================================

COMPOSE_DEV ?= docker compose -f docker-compose.yml --env-file .env
PROD_PROFILES ?=
COMPOSE_PROD ?= docker compose -f docker-compose.prod.yml $(PROD_PROFILES) --env-file .env.prod

.PHONY: help \
        check-env-dev check-env-prod setup \
        up down restart logs ps build rebuild \
        migrate makemigrations migrate-only seed createsuperadmin \
        shell-backend shell-frontend dbshell test lint fmt \
        clean-dev reset-migrations reset-all \
        prod-up prod-up-queue prod-up-full prod-down prod-restart prod-logs prod-ps \
        prod-build prod-rebuild prod-migrate prod-makemigrations prod-seed \
        prod-createsuperadmin prod-shell-backend prod-dbshell prod-stats \
        prod-update

# ============================================================
# Help
# ============================================================
help:
	@echo "RASMARA Makefile"
	@echo ""
	@echo "ATURAN ENV FILE (penting):"
	@echo "  DEV  -> .env       (target tanpa prefix, atau dev-*)"
	@echo "  PROD -> .env.prod  (target prefix prod-*)"
	@echo ""
	@echo "=== DEV (laptop, Docker Compose dev) ==="
	@echo "  make setup            copy .env.example -> .env (sekali pakai)"
	@echo "  make up               jalankan stack dev"
	@echo "  make down             matikan stack dev"
	@echo "  make logs             tail log semua service"
	@echo "  make ps               status container"
	@echo "  make migrate          makemigrations + migrate (dev)"
	@echo "  make seed             seed data awal (dev)"
	@echo "  make createsuperadmin buat superadmin (dev)"
	@echo "  make shell-backend    bash di container backend"
	@echo "  make dbshell          psql ke database"
	@echo "  make test             pytest backend"
	@echo "  make reset-all        nuklir: clean volumes + reset migrations"
	@echo ""
	@echo "=== PROD (VPS Debian 11) ==="
	@echo "  make prod-up                 stack default (postgres+backend+frontend+caddy)"
	@echo "  make prod-up-queue           + redis + celery (Modul 9 ke atas)"
	@echo "  make prod-up-full            + queue + s3 (MinIO)"
	@echo "  make prod-down               turunkan semua"
	@echo "  make prod-restart            restart stack"
	@echo "  make prod-logs               tail log"
	@echo "  make prod-stats              docker stats + free -h"
	@echo "  make prod-migrate            migrate (prod)"
	@echo "  make prod-seed               seed data (prod)"
	@echo "  make prod-createsuperadmin   buat superadmin (prod)"
	@echo "  make prod-shell-backend      bash container backend (prod)"
	@echo "  make prod-dbshell            psql (prod)"
	@echo "  make prod-update             git pull + rebuild + migrate + restart"
	@echo ""
	@echo "First deploy di VPS: bash deploy/debian11/02-app-bootstrap.sh"
	@echo "(script tsb sudah lakukan migrate + seed + createsuperadmin sekaligus)"

# ============================================================
# Validator: stop semua dev/prod target kalau env file tidak ada
# ============================================================
check-env-dev:
	@if [ ! -f .env ]; then \
		echo ""; \
		echo "[ERROR] File .env tidak ada."; \
		echo ""; \
		echo "Anda di MODE DEV. Jalankan dulu:"; \
		echo "    make setup    # auto copy .env.example -> .env"; \
		echo ""; \
		echo "Kalau Anda berniat MODE PROD (VPS), pakai prefix prod-*:"; \
		echo "    make prod-up      (bukan 'make up')"; \
		echo "    make prod-migrate (bukan 'make migrate')"; \
		echo "    make prod-seed    (bukan 'make seed')"; \
		echo "Prod butuh .env.prod (cp .env.example .env.prod)."; \
		echo ""; \
		exit 1; \
	fi

check-env-prod:
	@if [ ! -f .env.prod ]; then \
		echo ""; \
		echo "[ERROR] File .env.prod tidak ada."; \
		echo ""; \
		echo "Untuk mode PROD (VPS), siapkan dulu:"; \
		echo "    cp .env.example .env.prod"; \
		echo "    nano .env.prod    # ganti password & secret"; \
		echo ""; \
		echo "Kalau Anda berniat MODE DEV (laptop), pakai target tanpa prefix:"; \
		echo "    make up      (bukan 'make prod-up')"; \
		echo "    make migrate (bukan 'make prod-migrate')"; \
		echo "Dev butuh .env (make setup utk auto-copy)."; \
		echo ""; \
		exit 1; \
	fi

# ============================================================
# Setup
# ============================================================
setup:
	@if [ ! -f .env ]; then cp .env.example .env; echo "[OK] .env dibuat dari .env.example. Edit secret di .env."; else echo "[INFO] .env sudah ada."; fi

# ============================================================
# DEV
# ============================================================
up: check-env-dev
	$(COMPOSE_DEV) up -d
	@echo "Stack dev up. Akses:"
	@echo "  Frontend:        http://localhost"
	@echo "  Backend API:     http://localhost/api/v1/health/"
	@echo "  Mailpit (email): http://localhost:8025"
	@echo "  MinIO console:   http://localhost:9001"

down: check-env-dev
	$(COMPOSE_DEV) down

restart: check-env-dev
	$(COMPOSE_DEV) restart

logs: check-env-dev
	$(COMPOSE_DEV) logs -f --tail=200

ps: check-env-dev
	$(COMPOSE_DEV) ps

build: check-env-dev
	$(COMPOSE_DEV) build

rebuild: check-env-dev
	$(COMPOSE_DEV) build --no-cache

migrate: check-env-dev
	$(COMPOSE_DEV) run --rm backend bash -c "python manage.py makemigrations && python manage.py migrate"

makemigrations: check-env-dev
	$(COMPOSE_DEV) run --rm backend python manage.py makemigrations

migrate-only: check-env-dev
	$(COMPOSE_DEV) run --rm backend python manage.py migrate

seed: check-env-dev
	$(COMPOSE_DEV) run --rm backend python manage.py seed_initial_data

createsuperadmin: check-env-dev
	$(COMPOSE_DEV) run --rm backend python manage.py create_superadmin

shell-backend: check-env-dev
	$(COMPOSE_DEV) exec backend bash

shell-frontend: check-env-dev
	$(COMPOSE_DEV) exec frontend sh

dbshell: check-env-dev
	$(COMPOSE_DEV) exec postgres psql -U $${POSTGRES_USER:-rasmara} $${POSTGRES_DB:-rasmara}

test: check-env-dev
	$(COMPOSE_DEV) run --rm backend pytest

lint: check-env-dev
	$(COMPOSE_DEV) run --rm backend ruff check .
	$(COMPOSE_DEV) run --rm frontend npm run lint || true

fmt: check-env-dev
	$(COMPOSE_DEV) run --rm backend ruff format .
	$(COMPOSE_DEV) run --rm frontend npm run format || true

clean-dev: check-env-dev
	$(COMPOSE_DEV) down -v

reset-migrations:
	@echo "Hapus semua migration files (kecuali __init__.py) di apps/*/migrations/"
	find backend/apps -path '*/migrations/*.py' -not -name '__init__.py' -delete
	find backend/apps -path '*/migrations/__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "Selesai. Jalankan: make down && make up (auto-migrate akan generate ulang)"

reset-all: clean-dev reset-migrations
	@echo "Stack dev di-reset total. Jalankan: make up && make seed && make createsuperadmin"

# ============================================================
# PROD (VPS Debian 11)
# ============================================================
prod-up: check-env-prod
	$(COMPOSE_PROD) up -d
	@echo ""
	@echo "Stack prod up. Profiles aktif: '$(PROD_PROFILES)'"
	@echo "Akses via http://<IP_VPS> (port 80) atau https://<DOMAIN> jika sudah di-set."

prod-up-queue: check-env-prod
	docker compose -f docker-compose.prod.yml --profile queue --env-file .env.prod up -d
	@echo "Stack prod + queue (Redis + Celery worker + Celery beat) up."

prod-up-full: check-env-prod
	docker compose -f docker-compose.prod.yml --profile queue --profile s3 --env-file .env.prod up -d
	@echo "Stack prod + queue + s3 (MinIO) up."

prod-down: check-env-prod
	docker compose -f docker-compose.prod.yml --profile queue --profile s3 --env-file .env.prod down

prod-restart: check-env-prod
	$(COMPOSE_PROD) restart

prod-logs: check-env-prod
	$(COMPOSE_PROD) logs -f --tail=200

prod-ps: check-env-prod
	$(COMPOSE_PROD) ps

prod-stats:
	@echo "=== Container resource usage ==="
	@docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
	@echo ""
	@echo "=== Memory & swap ==="
	@free -h

prod-build: check-env-prod
	$(COMPOSE_PROD) build

prod-rebuild: check-env-prod
	$(COMPOSE_PROD) build --no-cache

prod-migrate: check-env-prod
	$(COMPOSE_PROD) run --rm backend bash -c "python manage.py makemigrations && python manage.py migrate --noinput"

prod-makemigrations: check-env-prod
	$(COMPOSE_PROD) run --rm backend python manage.py makemigrations

prod-seed: check-env-prod
	$(COMPOSE_PROD) run --rm backend python manage.py seed_initial_data

prod-createsuperadmin: check-env-prod
	$(COMPOSE_PROD) run --rm backend python manage.py create_superadmin

prod-shell-backend: check-env-prod
	$(COMPOSE_PROD) exec backend bash

prod-dbshell: check-env-prod
	$(COMPOSE_PROD) exec postgres psql -U $$(grep -E '^POSTGRES_USER=' .env.prod | cut -d= -f2) $$(grep -E '^POSTGRES_DB=' .env.prod | cut -d= -f2)

prod-update: check-env-prod
	bash deploy/debian11/03-update.sh
