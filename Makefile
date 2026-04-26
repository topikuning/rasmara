SHELL := /bin/bash
COMPOSE_DEV ?= docker compose -f docker-compose.yml --env-file .env
COMPOSE_PROD ?= docker compose -f docker-compose.prod.yml --env-file .env.prod

.PHONY: help setup up down restart logs ps build rebuild migrate makemigrations \
        seed createsuperadmin shell-backend shell-frontend dbshell test lint \
        fmt clean-dev prod-up prod-down prod-logs prod-build prod-migrate \
        prod-seed prod-createsuperadmin

help:
	@echo "RASMARA - perintah utama"
	@echo "  make setup            - copy .env.example -> .env (sekali pakai)"
	@echo "  make up               - jalankan stack dev (postgres,redis,minio,mailpit,backend,frontend,caddy)"
	@echo "  make down             - matikan stack dev"
	@echo "  make logs             - tail log semua service"
	@echo "  make migrate          - jalankan migrasi DB (dev)"
	@echo "  make seed             - seed data awal (role, permission, menu)"
	@echo "  make createsuperadmin - buat superadmin user"
	@echo "  make shell-backend    - bash di container backend"
	@echo "  make dbshell          - psql ke database"
	@echo "  make test             - jalankan pytest backend"
	@echo "  make lint             - ruff + mypy + eslint"
	@echo ""
	@echo "Production (di VPS Debian 11):"
	@echo "  make prod-up          - up stack production"
	@echo "  make prod-migrate     - migrate DB production"
	@echo "  make prod-seed        - seed data production"
	@echo "  make prod-createsuperadmin - buat superadmin di production"

setup:
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env from .env.example. Edit secrets di .env sebelum lanjut."; else echo ".env sudah ada."; fi

# ---- DEV ----
up:
	$(COMPOSE_DEV) up -d
	@echo "Stack dev up. Akses:"
	@echo "  Frontend:        http://localhost (port 80 via Caddy)"
	@echo "  Backend API:     http://localhost/api/v1/health"
	@echo "  Mailpit (email): http://localhost:8025"
	@echo "  MinIO console:   http://localhost:9001"

down:
	$(COMPOSE_DEV) down

restart:
	$(COMPOSE_DEV) restart

logs:
	$(COMPOSE_DEV) logs -f --tail=200

ps:
	$(COMPOSE_DEV) ps

build:
	$(COMPOSE_DEV) build

rebuild:
	$(COMPOSE_DEV) build --no-cache

migrate:
	$(COMPOSE_DEV) run --rm backend bash -c "python manage.py makemigrations && python manage.py migrate"

makemigrations:
	$(COMPOSE_DEV) run --rm backend python manage.py makemigrations

migrate-only:
	$(COMPOSE_DEV) run --rm backend python manage.py migrate

seed:
	$(COMPOSE_DEV) run --rm backend python manage.py seed_initial_data

createsuperadmin:
	$(COMPOSE_DEV) run --rm backend python manage.py create_superadmin

shell-backend:
	$(COMPOSE_DEV) exec backend bash

shell-frontend:
	$(COMPOSE_DEV) exec frontend sh

dbshell:
	$(COMPOSE_DEV) exec postgres psql -U $${POSTGRES_USER:-rasmara} $${POSTGRES_DB:-rasmara}

test:
	$(COMPOSE_DEV) run --rm backend pytest

lint:
	$(COMPOSE_DEV) run --rm backend ruff check .
	$(COMPOSE_DEV) run --rm frontend npm run lint || true

fmt:
	$(COMPOSE_DEV) run --rm backend ruff format .
	$(COMPOSE_DEV) run --rm frontend npm run format || true

clean-dev:
	$(COMPOSE_DEV) down -v

# ---- PROD (Debian 11 VPS) ----
prod-up:
	$(COMPOSE_PROD) up -d
	@echo "Stack prod up. Akses via http://<IP_VPS> (port 80) atau https://<DOMAIN> jika sudah di-set."

prod-down:
	$(COMPOSE_PROD) down

prod-logs:
	$(COMPOSE_PROD) logs -f --tail=200

prod-build:
	$(COMPOSE_PROD) build

prod-migrate:
	$(COMPOSE_PROD) run --rm backend python manage.py migrate

prod-seed:
	$(COMPOSE_PROD) run --rm backend python manage.py seed_initial_data

prod-createsuperadmin:
	$(COMPOSE_PROD) run --rm backend python manage.py create_superadmin
