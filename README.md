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

### Profil Stack (sesuaikan dengan ukuran VPS)

Stack default dirancang untuk **VPS 1 vCPU + 2 GB RAM**.

| Profil | Service aktif | RAM idle ± | Cocok utk |
|---|---|---|---|
| default (tanpa flag) | postgres + backend + frontend + caddy | ~600 MB | Modul 1–4, VPS minimal |
| `--profile queue` | + redis + celery-worker + celery-beat | + ~250 MB | Saat Modul 9 (notifikasi/scheduler) aktif |
| `--profile s3` | + minio | + ~200 MB | Volume foto besar (storage S3) |

### VPS 1 vCPU + 2 GB RAM

Repo bebas diletakkan di mana saja (mis. `~/rasmara`, `/opt/rasmara/app`,
`/home/rasmara/rasmara`) — script auto-derive path.

```bash
# Misal repo Anda di ~/rasmara :
cd ~/rasmara
cp .env.example .env.prod
nano .env.prod                # ganti password & secret. SITE_ADDRESS biarkan ":80".

bash deploy/debian11/02-app-bootstrap.sh
# Akses: http://<IP_VPS_ANDA>
```

Data volume Docker (postgres, media, dst.) otomatis dibuat di `<repo>/data/`,
backup di `<repo>/backups/`. Override via env: `DATA_DIR=/path/lain bash ...`.

Cek konsumsi resource real-time:
```bash
make prod-stats               # docker stats + free -h
```

### Mengaktifkan profil tambahan saat dibutuhkan
```bash
make prod-up-queue            # default + queue (Modul 9)
make prod-up-full             # default + queue + s3
```

### Aktifkan HTTPS + domain
Edit `.env.prod`:
```
DOMAIN=rasmara.example.go.id
SITE_ADDRESS=https://rasmara.example.go.id
```
lalu `make prod-up`. Caddy auto-fetch sertifikat Let's Encrypt.

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
