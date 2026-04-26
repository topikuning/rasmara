# Deployment RASMARA ke VPS Debian 11

Manual ini menjelaskan **langkah lengkap** memasang RASMARA di VPS Debian 11 (Bullseye)
dari kondisi server bersih sampai aplikasi bisa diakses **via IP di port 80** (HTTP).
Setelah Anda punya domain & DNS terarah, switch ke HTTPS hanya butuh edit 1 baris env.

---

## Ringkasan Arus Akses

```
Pengunjung (browser)
       │  HTTP
       v
+------------------+      :80 / :443
|  Caddy (proxy)   |  ← reverse proxy + auto TLS (jika DOMAIN diisi)
+------------------+
   ├── /api/*       →  backend:8000  (Django + DRF)
   ├── /django-admin/ → backend:8000
   ├── /static/*    →  backend:8000
   ├── /media/*     →  backend:8000
   └── (lainnya)    →  frontend:3000  (Next.js)
```

- **Mode IP** (default awal): `SITE_ADDRESS=:80`. Anda akses `http://<IP_VPS>` langsung.
- **Mode Domain**: `SITE_ADDRESS=https://your-domain.tld` + `DOMAIN=your-domain.tld`.
  Caddy ambil sertifikat Let's Encrypt otomatis. **Tidak perlu certbot manual**.

---

## 0. Prasyarat

| Item | Minimum | Direkomendasikan |
|---|---|---|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| Disk | 50 GB SSD | 100 GB SSD |
| OS | Debian 11 (Bullseye) bersih | |

Yang harus Anda siapkan sebelum mulai:
1. Akses **SSH root** ke VPS (atau user dengan sudo).
2. **IP publik** VPS sudah diketahui.
3. (Opsional, untuk HTTPS): **domain** dengan DNS A-record mengarah ke IP VPS.
4. **SSH public key** Anda di clipboard / file lokal.
5. (Opsional): kredensial SMTP untuk notifikasi email.

---

## 1. Bootstrap Server (sekali pakai, sebagai root)

Login SSH sebagai `root`:

```bash
ssh root@<IP_VPS>
```

Clone repo (atau upload tar bila tidak ada git):

```bash
apt update && apt install -y git
mkdir -p /opt/rasmara
cd /opt/rasmara
git clone https://github.com/topikuning/rasmara.git app
cd app
```

Jalankan script bootstrap (akan: install paket dasar, buat user `rasmara`, copy SSH key,
hardening SSH, firewall ufw, fail2ban, swap 4GB, set timezone Asia/Jakarta):

```bash
bash deploy/debian11/00-prerequisites.sh
```

**Penting:** script akan men-disable login root via SSH. Pastikan Anda sudah
men-copy SSH public key Anda ke `/root/.ssh/authorized_keys` SEBELUM menjalankan
script ini, karena script akan menyalin authorized_keys ke `rasmara` user.

Selanjutnya **logout dan login ulang sebagai `rasmara`**:

```bash
exit
ssh rasmara@<IP_VPS>
```

---

## 2. Install Docker & Docker Compose

Sebagai user `rasmara`:

```bash
cd /opt/rasmara/app
sudo bash deploy/debian11/01-docker.sh
# Setelah selesai, logout-login sekali lagi agar group `docker` aktif:
exit
ssh rasmara@<IP_VPS>
docker --version          # cek
docker compose version    # cek
```

---

## 3. Konfigurasi Environment

```bash
cd /opt/rasmara/app
cp .env.example .env.prod
nano .env.prod
```

Isi minimal yang **WAJIB diganti**:
- `DJANGO_SECRET_KEY` → string random ≥ 50 karakter (bisa pakai `openssl rand -base64 60`)
- `POSTGRES_PASSWORD` → password random
- `MINIO_ROOT_PASSWORD` → password random
- `SUPERADMIN_PASSWORD` → password awal Superadmin (akan dipaksa ganti saat login pertama)
- `ADMIN_EMAIL` → email kontak admin (untuk Let's Encrypt nanti)

**Untuk akses awal via IP**, biarkan field berikut **default**:
```
SITE_ADDRESS=:80
DOMAIN=
```

---

## 4. Build & Bring Up

Script bootstrap aplikasi akan: build images, init DB, jalankan migrate + seed,
buat superadmin, dan up semua service.

```bash
cd /opt/rasmara/app
sudo bash deploy/debian11/02-app-bootstrap.sh
```

Tunggu sampai output: `[OK] RASMARA UP. Akses: http://<IP_VPS>`.

**Cek dari laptop Anda:**
```bash
curl -I http://<IP_VPS>/api/v1/health/    # harus 200 OK
```
Atau buka browser ke `http://<IP_VPS>`.

---

## 5. Login Pertama

1. Akses `http://<IP_VPS>` di browser. Anda akan lihat halaman utama RASMARA.
2. Klik **Masuk ke Sistem** atau buka langsung `http://<IP_VPS>/login`.
3. Login pakai:
   - Username: nilai `SUPERADMIN_USERNAME` di `.env.prod` (default: `superadmin`)
   - Password: nilai `SUPERADMIN_PASSWORD` di `.env.prod`
4. Sistem akan **memaksa Anda mengganti password** karena `must_change_password=true`.
5. Setelah ganti password → masuk ke Dashboard.

---

## 6. Auto-Start saat Reboot (systemd)

Pasang service systemd supaya stack aktif kembali setelah VPS reboot:

```bash
cd /opt/rasmara/app
sudo cp deploy/debian11/systemd/rasmara.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rasmara.service
sudo systemctl status rasmara.service
```

---

## 7. Backup Otomatis Harian

```bash
cd /opt/rasmara/app
sudo cp deploy/debian11/systemd/rasmara-backup.service /etc/systemd/system/
sudo cp deploy/debian11/systemd/rasmara-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rasmara-backup.timer
sudo systemctl list-timers | grep rasmara
```

Backup tersimpan di `/opt/rasmara/backups/`. Retention: 14 hari (script).

---

## 8. Aktifkan HTTPS dengan Domain (Setelah Punya Domain)

1. Pastikan DNS A-record `your-domain.tld` mengarah ke IP VPS dan sudah propagasi:
   ```bash
   dig +short your-domain.tld
   ```
2. Edit `.env.prod`:
   ```
   DOMAIN=your-domain.tld
   SITE_ADDRESS=https://your-domain.tld
   DJANGO_ALLOWED_HOSTS=your-domain.tld
   DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.tld
   ```
3. Restart Caddy:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --no-deps caddy
   docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f caddy
   ```
   Tunggu sampai log Caddy menunjukkan sertifikat berhasil di-issue.
4. Akses `https://your-domain.tld` — padlock hijau.

---

## 9. Update Aplikasi

Saat ada rilis baru:

```bash
cd /opt/rasmara/app
git fetch origin
git checkout <branch-or-tag>
sudo bash deploy/debian11/03-update.sh
```

Script akan: pull, build, migrate, restart service yang kena perubahan.

---

## 10. Troubleshooting

| Masalah | Cek |
|---|---|
| `curl -I http://<IP>/api/v1/health/` connection refused | `docker compose ps`, port 80 tidak terbuka, ufw aktifkan: `sudo ufw allow 80/tcp` |
| 502 Bad Gateway | `docker compose logs backend` — cek error startup Django |
| Login gagal terus | Reset Superadmin: `make prod-createsuperadmin` (atau `--reset` flag) |
| Lupa password Superadmin | `docker compose -f docker-compose.prod.yml run --rm backend python manage.py create_superadmin --reset` |
| Disk penuh | `du -sh /opt/rasmara/data/*`, biasanya MinIO atau PostgreSQL WAL |
| Email tidak terkirim | Cek tabel `notification_queue` (status FAILED + last_error). Test SMTP manual via mailpit lokal dulu untuk validasi env |
| Container tidak auto-up after reboot | `systemctl status rasmara.service` |
| Sertifikat TLS gagal | Cek port 80 terbuka, DNS sudah propagasi, `docker compose logs caddy` |

---

## 11. Checklist Go-Live

- [ ] DNS A-record (kalau pakai domain) sudah propagasi
- [ ] SSH key-only login, root login disabled
- [ ] UFW aktif (22, 80, 443 saja)
- [ ] fail2ban aktif
- [ ] Swap 4GB aktif
- [ ] Timezone `Asia/Jakarta`
- [ ] Docker + compose terinstall
- [ ] `.env.prod` terisi penuh, password random
- [ ] Aplikasi nyala via http://<IP>/
- [ ] `/api/v1/health/ready/` return 200
- [ ] Login Superadmin berhasil, bisa ganti password
- [ ] Test SMTP kirim email reset password
- [ ] Backup manual berhasil (`bash deploy/debian11/backup.sh`)
- [ ] Restore di environment terpisah berhasil
- [ ] Systemd service & backup timer aktif
- [ ] Monitoring uptime ping berjalan (Uptime Kuma di server lain — opsional)
