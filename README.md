# RASMARA

**Real-time Analytics System for Monitoring, Allocation, Reporting & Accountability**

Sistem monitoring pelaksanaan kontrak konstruksi infrastruktur — khususnya proyek
pemerintahan, dengan compliance Perpres 16/2018 ps. 54 (perubahan kontrak via
Addendum/CCO).

Spesifikasi fungsional lengkap ada di [`CLAUDE.md`](./CLAUDE.md).

---

## Stack

- **Backend**: Django 5 + DRF + JWT + Celery + Celery Beat
- **Database**: PostgreSQL 16 (JSONB, partial unique index)
- **Cache & Queue**: Redis 7
- **File storage**: MinIO (S3 compatible)
- **Frontend**: Next.js 15 + React + TypeScript + Tailwind + shadcn/ui
- **Grid Excel-like**: Glide Data Grid (BOQ & laporan mingguan), AG Grid Community (grid lain)
- **Chart**: Apache ECharts
- **Peta**: Leaflet + OpenStreetMap
- **PDF**: WeasyPrint
- **Excel**: openpyxl + xlsxwriter
- **Reverse proxy + auto TLS**: Caddy 2
- **Container**: Docker + Docker Compose

Semua **open source / gratis**.

---

## Quick Start - Pengembangan Lokal

```bash
# 1. Setup env file
make setup
nano .env   # ganti secret bila perlu

# 2. Build & up
make build
make up

# 3. Migrasi & seed
make migrate
make seed
make createsuperadmin

# 4. Akses
# Frontend:        http://localhost
# Backend API:     http://localhost/api/v1/health/
# Mailpit (email): http://localhost:8025
# MinIO console:   http://localhost:9001
```

---

## Deployment ke VPS Debian 11

Manual lengkap step-by-step ada di [`deploy/debian11/README.md`](./deploy/debian11/README.md).

Ringkasan **akses awal via IP di port 80** (tanpa domain):

```bash
# Di VPS sebagai user 'rasmara' (sudah dibuat oleh script bootstrap)
cd /opt/rasmara/app
cp .env.example .env.prod
nano .env.prod                # isi POSTGRES_PASSWORD, MINIO password, dll.
                              # SITE_ADDRESS biarkan ":80" (default)
                              # DOMAIN biarkan kosong

make prod-build
make prod-migrate
make prod-seed
make prod-createsuperadmin
make prod-up

# Akses: http://<IP_VPS_ANDA>
```

Untuk aktifkan HTTPS+domain: edit `.env.prod`:
```
DOMAIN=rasmara.example.go.id
SITE_ADDRESS=https://rasmara.example.go.id
```
lalu `make prod-up` ulang. Caddy akan auto-fetch sertifikat Let's Encrypt.

---

## Struktur Repo

```
rasmara/
├── CLAUDE.md                 # spesifikasi fungsional (sumber kebenaran)
├── README.md
├── docker-compose.yml        # dev stack
├── docker-compose.prod.yml   # prod stack
├── .env.example
├── Makefile
├── backend/                  # Django + DRF
├── frontend/                 # Next.js 15
├── deploy/debian11/          # script & manual deploy ke VPS
└── docs/
```

Detail lihat dokumen arsitektur di `docs/`.

---

## Modul-modul (Implementasi Bertahap)

1. **Fondasi** — Auth, RBAC dinamis, Audit log, Notification queue skeleton
2. **Master Data** — Company, PPK, Master Facility, Master Work Code
3. **Kontrak + Lokasi + Fasilitas** + gate aktivasi
4. **BOQ** — versioning V0/V1, hirarki 4 level, import/export, komparasi revisi
5. **VO + Addendum** — state machine, KPA threshold, auto-clone revisi BOQ
6. **Pelaporan** — Harian, Mingguan, Field Observation MC, Field Review Itjen
7. **Termin Pembayaran** — state machine, anchor BOQ revision saat SUBMIT
8. **Dashboard Eksekutif** — peta interaktif, kurva-S, galeri foto
9. **Notifikasi & Early Warning**
10. **Hardening** — PDF/Excel mature, performa virtualisasi, edge case

Status saat ini: **Modul 1 dalam pengerjaan**.

---

## Lisensi

Internal. Lihat tim untuk detail.
