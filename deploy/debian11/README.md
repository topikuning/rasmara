# Deployment RASMARA ke VPS Debian 11

Manual ini menjelaskan **langkah lengkap** memasang RASMARA di VPS Debian 11 (Bullseye)
dari kondisi server bersih sampai aplikasi bisa diakses **via IP di port 80** (HTTP).

## Prinsip Path

**Tidak ada path hardcoded.** Semua script di folder ini menurunkan path repo
secara otomatis dari lokasi script-nya sendiri:

```
<repo>/                       <- bisa di mana saja: ~/rasmara, /opt/rasmara/app,
├── docker-compose.prod.yml      /home/user/projects/rasmara, dst.
├── .env.prod
├── data/                     <- volume Docker (auto-dibuat oleh script)
│   ├── postgres/
│   ├── backend-static/
│   ├── backend-media/
│   └── caddy/
├── backups/                  <- backup harian (auto-dibuat)
└── deploy/debian11/          <- script-script ini
    ├── 00-prerequisites.sh
    ├── 01-docker.sh
    ├── 02-app-bootstrap.sh
    ├── 03-update.sh
    ├── backup.sh / restore.sh
    └── install-systemd.sh
```

Kalau perlu override path, tersedia env var:
- `REPO_DIR` — default: derive dari lokasi script
- `DATA_DIR` — default: `$REPO_DIR/data`
- `BACKUP_DIR` — default: `$REPO_DIR/backups`
- `ENVF` — default: `.env.prod`
- `PROFILES` — default: kosong (stack default)

---

## Spesifikasi Minimum

| Resource | Minimum | Direkomendasikan |
|---|---|---|
| CPU | 1 vCPU | 2+ vCPU |
| RAM | 2 GB (+ 4GB swap) | 4 GB |
| Disk | 20 GB SSD | 50 GB SSD |
| OS | Debian 11 | |

---

## 0. Prasyarat

1. SSH root ke VPS.
2. SSH public key Anda sudah ada di `/root/.ssh/authorized_keys` SEBELUM lanjut.
3. (Opsional) domain dengan A-record ke IP VPS — untuk HTTPS.

---

## 1. Bootstrap Server (sekali pakai, sebagai root)

```bash
ssh root@<IP_VPS>

# Pilih lokasi repo. Bebas — di bawah ini contoh /home/rasmara:
mkdir -p /home && cd /home
apt update && apt install -y git
# (jika user 'rasmara' belum ada, dibuat oleh 00-prerequisites.sh nanti)

# Clone repo (git ke folder pilihan Anda)
git clone -b claude/study-api-timeout-1mtuQ https://github.com/topikuning/rasmara.git
cd rasmara

# Bootstrap OS (firewall, swap, user 'rasmara' + SSH key, dll.)
bash deploy/debian11/00-prerequisites.sh
```

Script akan disable login root via SSH. **Pastikan SSH public key sudah ter-copy ke
authorized_keys dulu**, karena script akan menyalin ke user `rasmara`.

Logout dan login ulang sebagai `rasmara`. Pindahkan repo (kalau perlu) ke
folder yang aksesnya sesuai user `rasmara`:

```bash
exit
ssh rasmara@<IP_VPS>

# Pindahkan repo agar dapat diakses tanpa sudo (opsional)
sudo mv /home/rasmara /home/rasmara-old || true   # jika ada konflik
sudo mv /root/rasmara /home/rasmara/rasmara 2>/dev/null || true
# atau clone ulang sebagai rasmara
cd ~
git clone -b claude/study-api-timeout-1mtuQ https://github.com/topikuning/rasmara.git
cd rasmara
```

---

## 2. Install Docker

```bash
sudo bash deploy/debian11/01-docker.sh
# Logout-login sekali lagi agar group 'docker' aktif:
exit
ssh rasmara@<IP_VPS>
cd ~/rasmara
docker compose version
```

---

## 3. Konfigurasi Environment

```bash
cp .env.example .env.prod
nano .env.prod
```

Isi minimal yang **WAJIB diganti**:
- `DJANGO_SECRET_KEY` → string random ≥50 karakter (`openssl rand -base64 60`)
- `POSTGRES_PASSWORD` → password random
- `SUPERADMIN_PASSWORD` → password awal Superadmin
- `ADMIN_EMAIL` → email kontak admin

Untuk akses awal via IP, biarkan default:
```
SITE_ADDRESS=:80
DOMAIN=
```

---

## 4. Build & Bring Up

```bash
bash deploy/debian11/02-app-bootstrap.sh
```

Script akan:
- Cek RAM & swap (peringatan kalau <2GB)
- Buat folder `./data/...` & `./backups/`
- Build images
- Start postgres → migrate → seed → create_superadmin
- Start full stack (default profile: postgres + backend + frontend + caddy)

Tunggu output:
```
[OK] RASMARA UP.
Akses: http://<IP_VPS>     (mode IP / port 80, HTTP)
```

Cek RAM:
```bash
docker stats --no-stream
free -h
```

---

## 5. Login Pertama

1. Buka `http://<IP_VPS>` di browser → halaman utama RASMARA.
2. Klik **Masuk ke Sistem** atau buka `http://<IP_VPS>/login`.
3. Login: `superadmin` + password dari `.env.prod`.
4. Sistem paksa ganti password.
5. Setelah ganti → masuk Dashboard.

---

## 6. Auto-Start saat Reboot (systemd)

```bash
sudo bash deploy/debian11/install-systemd.sh
```

Script akan render template `*.service.template` (mengganti `__REPO_DIR__` dan
`__USER__` sesuai lokasi & user aktif), pasang ke `/etc/systemd/system/`,
enable + start `rasmara.service` dan `rasmara-backup.timer` (jam 02:00 WIB harian).

Cek:
```bash
systemctl status rasmara.service
systemctl list-timers | grep rasmara
```

---

## 7. Aktifkan HTTPS dengan Domain

1. DNS A record `your-domain.tld` → IP VPS, propagasi:
   ```bash
   dig +short your-domain.tld
   ```
2. Edit `.env.prod`:
   ```
   DOMAIN=your-domain.tld
   SITE_ADDRESS=https://your-domain.tld
   DJANGO_ALLOWED_HOSTS=your-domain.tld
   ```
3. Restart Caddy:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --no-deps caddy
   docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f caddy
   ```
4. Akses `https://your-domain.tld` — padlock hijau.

---

## 8. Update Aplikasi

```bash
bash deploy/debian11/03-update.sh
```

---

## 9. Aktifkan Profile Tambahan

Stack default tidak menjalankan Redis/Celery/MinIO. Saat dibutuhkan:

```bash
# Tambah queue (Modul 9 — notifikasi & scheduler):
PROFILES='--profile queue' bash deploy/debian11/02-app-bootstrap.sh

# Tambah queue + s3:
PROFILES='--profile queue --profile s3' bash deploy/debian11/02-app-bootstrap.sh
```

---

## 10. Restore dari Backup

```bash
bash deploy/debian11/restore.sh ./backups/db_20260426_020000.sql.gz
```

---

## 11. Troubleshooting

| Masalah | Cek |
|---|---|
| 502 Bad Gateway | `docker compose ps`, `docker compose logs backend` |
| Sertifikat TLS gagal | DNS sudah propagasi? Port 80 terbuka? `docker compose logs caddy` |
| OOM saat build | `free -h` — pastikan swap aktif. Pakai `make prod-up` (default profile) tanpa queue/s3 |
| Login gagal | Reset Superadmin: `docker compose run --rm backend python manage.py create_superadmin --reset` |
| Disk penuh | `du -sh ./data/* ./backups/*` |
| Container tidak auto-up after reboot | `systemctl status rasmara.service` |

---

## 12. Checklist Go-Live

- [ ] DNS A-record propagasi (kalau pakai domain)
- [ ] SSH key-only login, root disabled
- [ ] UFW aktif (22, 80, 443)
- [ ] fail2ban aktif
- [ ] Swap 4GB
- [ ] Timezone Asia/Jakarta
- [ ] Docker + compose terinstall
- [ ] `.env.prod` random password
- [ ] Aplikasi nyala via http://<IP>/
- [ ] `/api/v1/health/ready/` 200
- [ ] Login Superadmin berhasil
- [ ] Test SMTP kirim email
- [ ] `bash deploy/debian11/backup.sh` berhasil
- [ ] `systemctl status rasmara.service` aktif
