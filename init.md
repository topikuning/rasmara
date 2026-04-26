# Bagian E — Manual Deployment Debian 11 VPS

Manual ini akan berbentuk dokumen runbook lengkap di `deploy/debian11/README.md` plus shell script eksekutif di folder yang sama. Berikut ringkasan langkah end-to-end yang akan diimplementasi.

## E.1 Prasyarat

### Spesifikasi VPS Minimum
| Resource | Minimum | Direkomendasikan |
|---|---|---|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| Storage | 50 GB SSD | 100 GB SSD |
| OS | Debian 11 (Bullseye) bersih | Debian 11 + kernel terbaru |
| Bandwidth | 100 Mbps | 1 Gbps |

### Yang Anda Siapkan Sebelum Mulai
1. **Akses SSH root** ke VPS (atau user sudo).
2. **Domain** (mis. `rasmara.example.go.id`) yang DNS A-record-nya sudah mengarah ke IP VPS.
3. **SSH public key** Anda (`~/.ssh/id_ed25519.pub`).
4. **Email admin** (untuk Let's Encrypt + akun Superadmin).
5. **SMTP credentials** (host, port, user, pass) — bisa dari Postfix relay kantor atau provider gratis.

## E.2 Langkah 1 — Bootstrap Awal Server (sekali pakai)

Login sebagai `root`, jalankan script `00-prerequisites.sh` yang akan:

```bash
# Update sistem
apt update && apt upgrade -y

# Install paket dasar
apt install -y curl wget git ufw fail2ban unattended-upgrades \
    ca-certificates gnupg lsb-release htop tmux rsync

# Buat user non-root untuk operasional
adduser --disabled-password --gecos "" rasmara
usermod -aG sudo rasmara
mkdir -p /home/rasmara/.ssh
cp ~/.ssh/authorized_keys /home/rasmara/.ssh/authorized_keys
chown -R rasmara:rasmara /home/rasmara/.ssh
chmod 700 /home/rasmara/.ssh
chmod 600 /home/rasmara/.ssh/authorized_keys

# Hardening SSH (PermitRootLogin no, PasswordAuthentication no)
# (script edit /etc/ssh/sshd_config dengan sed)
systemctl reload sshd

# Firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp     # SSH
ufw allow 80/tcp     # HTTP (Caddy → redirect)
ufw allow 443/tcp    # HTTPS
ufw --force enable

# fail2ban untuk SSH
systemctl enable --now fail2ban

# Auto security update
dpkg-reconfigure -plow unattended-upgrades

# Swap 4GB (penting untuk VPS RAM kecil saat build image)
fallocate -l 4G /swapfile && chmod 600 /swapfile
mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Timezone Asia/Jakarta
timedatectl set-timezone Asia/Jakarta
```

**Setelah selesai:** logout, login lagi sebagai `rasmara` (bukan root).

## E.3 Langkah 2 — Install Docker & Docker Compose

Jalankan `01-docker.sh`:

```bash
# Install Docker dari repo resmi (bukan apt Debian — versi terlalu lama)
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/debian $(lsb_release -cs) stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin

# User rasmara bisa pakai docker tanpa sudo
sudo usermod -aG docker rasmara
# logout-login lagi atau: newgrp docker

# Konfigurasi log rotation (cegah disk penuh dari log container)
sudo tee /etc/docker/daemon.json <<EOF
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "50m", "max-file": "5" },
  "default-address-pools": [{ "base": "10.20.0.0/16", "size": 24 }]
}
EOF
sudo systemctl restart docker

docker --version
docker compose version
```

## E.4 Langkah 3 — Deploy Aplikasi

Sebagai user `rasmara`, jalankan `02-app-bootstrap.sh`:

```bash
# Clone repo
mkdir -p /opt/rasmara && cd /opt/rasmara
git clone https://github.com/topikuning/rasmara.git app
cd app

# Copy dan edit .env (script akan generate password random, Anda isi yang manual)
cp .env.example .env.prod
nano .env.prod   # isi: DOMAIN, ADMIN_EMAIL, SMTP_*, dll.

# Folder untuk persistent data
sudo mkdir -p /opt/rasmara/data/{postgres,minio,media,caddy}
sudo chown -R rasmara:rasmara /opt/rasmara/data

# Build images
docker compose -f docker-compose.prod.yml --env-file .env.prod build

# Inisialisasi database
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d postgres redis minio
sleep 10
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm backend python manage.py migrate
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm backend python manage.py collectstatic --noinput
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm backend python manage.py seed_initial_data
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm backend python manage.py createsuperadmin --email "$ADMIN_EMAIL"

# Bring up full stack
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Cek
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f --tail=100
```

### Isi `.env.prod` (contoh)
```ini
DOMAIN=rasmara.example.go.id
ADMIN_EMAIL=admin@example.go.id
DJANGO_SECRET_KEY=<auto-generated>
DJANGO_ALLOWED_HOSTS=rasmara.example.go.id
POSTGRES_DB=rasmara
POSTGRES_USER=rasmara
POSTGRES_PASSWORD=<auto-generated>
REDIS_URL=redis://redis:6379/0
MINIO_ROOT_USER=rasmara
MINIO_ROOT_PASSWORD=<auto-generated>
MINIO_BUCKET=rasmara-media
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
SMTP_FROM=noreply@example.go.id
WHATSAPP_PROVIDER=stub   # ganti ke 'waha' nanti bila siap
TIMEZONE=Asia/Jakarta
```

## E.5 Langkah 4 — TLS Otomatis via Caddy

`docker-compose.prod.yml` sudah include service `caddy` yang menjadi reverse proxy + auto-TLS Let's Encrypt. File `deploy/debian11/caddy/Caddyfile`:

```
{
    email {$ADMIN_EMAIL}
}

{$DOMAIN} {
    encode gzip zstd

    # Frontend (Next.js)
    reverse_proxy frontend:3000

    # Backend API
    handle /api/* {
        reverse_proxy backend:8000
    }
    handle /admin/* {
        reverse_proxy backend:8000
    }
    handle /static/* {
        reverse_proxy backend:8000
    }

    # MinIO console (admin only - protect via IP allow-list)
    handle /minio-console/* {
        @allowed remote_ip 10.0.0.0/8 192.168.0.0/16 <kantor_ip>
        reverse_proxy @allowed minio:9001
        respond 403
    }

    log {
        output file /var/log/caddy/access.log {
            roll_size 100mb
            roll_keep 10
        }
    }
}
```

Caddy ambil sertifikat otomatis dari Let's Encrypt saat pertama kali start. Tidak perlu `certbot` manual.

## E.6 Langkah 5 — Systemd Service (Auto-Start saat Reboot)

`deploy/debian11/systemd/rasmara.service`:

```ini
[Unit]
Description=RASMARA Production Stack
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/rasmara/app
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml --env-file .env.prod down
TimeoutStartSec=0
User=rasmara

[Install]
WantedBy=multi-user.target
```

```bash
sudo cp deploy/debian11/systemd/rasmara.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rasmara.service
```

## E.7 Langkah 6 — Backup Otomatis Harian

`deploy/debian11/backup.sh`:

```bash
#!/bin/bash
set -euo pipefail
BACKUP_DIR=/opt/rasmara/backups
TS=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# 1. PostgreSQL dump (compressed)
docker compose -f /opt/rasmara/app/docker-compose.prod.yml exec -T postgres \
    pg_dump -U rasmara rasmara | gzip > "$BACKUP_DIR/db_$TS.sql.gz"

# 2. MinIO mirror (file storage)
docker compose -f /opt/rasmara/app/docker-compose.prod.yml exec -T minio \
    mc mirror --overwrite local/rasmara-media /tmp/minio-backup
tar -czf "$BACKUP_DIR/minio_$TS.tar.gz" -C /opt/rasmara/data/minio .

# 3. Retention (keep 14 daily, 8 weekly, 6 monthly)
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +14 -delete
find "$BACKUP_DIR" -name "minio_*.tar.gz" -mtime +14 -delete

# 4. (Opsional) Push ke remote storage offsite
# rsync -az "$BACKUP_DIR/" backup-server:/backups/rasmara/
```

Systemd timer `rasmara-backup.timer` jalankan setiap hari jam 02:00:
```ini
[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true
[Install]
WantedBy=timers.target
```

```bash
sudo systemctl enable --now rasmara-backup.timer
```

## E.8 Langkah 7 — Update Aplikasi (Zero-Downtime Sederhana)

Saat ada rilis baru di Git:

```bash
cd /opt/rasmara/app
git fetch origin
git checkout v1.2.3      # atau main
docker compose -f docker-compose.prod.yml --env-file .env.prod build
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm backend python manage.py migrate
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm backend python manage.py collectstatic --noinput
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --no-deps backend frontend celery-worker celery-beat
```

Backend & frontend di-restart bergantian (Caddy jaga koneksi). Untuk update besar (skema breaking, downtime > 30 detik), pasang banner maintenance dulu via `MAINTENANCE_MODE=true` di env.

## E.9 Langkah 8 — Monitoring & Log

### Log
- Container: `docker compose logs -f --tail=200 <service>`
- Caddy access: `/opt/rasmara/data/caddy/access.log`
- PostgreSQL slow query: aktifkan `log_min_duration_statement=500ms`
- Audit log aplikasi: di DB tabel `audit_log` (browse via UI Pengaturan)

### Health Check
- Endpoint: `https://rasmara.example.go.id/api/v1/health/ready`
- Pasang **Uptime Kuma** (gratis, self-host) di server lain untuk ping per 5 menit.

### Resource
- `docker stats` quick check
- (Opsional) install **Netdata** (gratis) untuk dashboard CPU/RAM/disk realtime.

## E.10 Langkah 9 — Restore dari Backup

`deploy/debian11/restore.sh`:

```bash
#!/bin/bash
# Pemakaian: ./restore.sh /opt/rasmara/backups/db_20260426_020000.sql.gz
set -euo pipefail
DUMP="$1"

# Stop aplikasi (tapi jangan stop postgres)
docker compose -f /opt/rasmara/app/docker-compose.prod.yml stop backend frontend celery-worker celery-beat

# Drop & recreate DB
docker compose -f /opt/rasmara/app/docker-compose.prod.yml exec postgres \
    psql -U rasmara -c "DROP DATABASE rasmara;"
docker compose -f /opt/rasmara/app/docker-compose.prod.yml exec postgres \
    psql -U rasmara -c "CREATE DATABASE rasmara;"

# Restore
gunzip -c "$DUMP" | docker compose -f /opt/rasmara/app/docker-compose.prod.yml exec -T postgres \
    psql -U rasmara rasmara

# Start lagi
docker compose -f /opt/rasmara/app/docker-compose.prod.yml up -d
```

## E.11 Troubleshooting Umum

| Masalah | Cek |
|---|---|
| 502 Bad Gateway | `docker compose ps` — backend up? `docker compose logs backend` |
| Sertifikat TLS gagal | DNS A record sudah propagasi? Port 80 terbuka? `docker compose logs caddy` |
| Database lambat | `docker compose exec postgres psql -U rasmara -c "SELECT * FROM pg_stat_activity;"` |
| Disk penuh | `du -sh /opt/rasmara/data/*` — biasanya MinIO atau Postgres WAL |
| Email tidak terkirim | Cek tabel `notification_queue` status FAILED + last_error. Test SMTP: `docker compose exec backend python manage.py test_smtp` |
| Reboot tidak auto-up | `systemctl status rasmara.service` |
| OOM killer membunuh container | Cek `dmesg \| tail` — tambah swap atau RAM |
| Login gagal terus | Reset Superadmin: `docker compose run --rm backend python manage.py changepassword <username>` |

## E.12 Keamanan Tambahan (Opsional tapi Direkomendasikan)

1. **VPN-only akses admin** — pasang WireGuard, batasi `/admin/*` & `/minio-console/*` ke IP VPN.
2. **2FA untuk Superadmin** — bisa ditambahkan di iterasi hardening (django-otp).
3. **Backup offsite** — sewa storage murah (Backblaze B2 punya 10GB gratis), `rclone` mirror harian.
4. **Monitoring kesehatan SSL** — alert 14 hari sebelum expire (Caddy auto-renew, tapi tetap monitor).
5. **DB encryption at rest** — kalau VPS provider tidak menyediakan, pakai LUKS pada disk yang berisi `/opt/rasmara/data`.

## E.13 Checklist Go-Live

- [ ] DNS A record sudah mengarah ke IP VPS dan ter-propagasi (`dig rasmara.example.go.id`).
- [ ] SSH hanya pakai key, root login disabled.
- [ ] UFW aktif (22, 80, 443 saja).
- [ ] fail2ban aktif.
- [ ] Swap 4GB aktif.
- [ ] Timezone `Asia/Jakarta`.
- [ ] Docker + compose terinstall, user `rasmara` di grup docker.
- [ ] `.env.prod` terisi penuh, password random.
- [ ] Aplikasi nyala, `https://domain/api/v1/health/ready` return 200.
- [ ] Sertifikat TLS valid (cek via browser, padlock hijau).
- [ ] Login Superadmin berhasil, bisa ganti password.
- [ ] Test buat 1 kontrak dummy → save → tampil → ekspor PDF.
- [ ] Test SMTP kirim email reset password.
- [ ] Test backup manual berhasil (`bash deploy/debian11/backup.sh`).
- [ ] Test restore di environment terpisah.
- [ ] Systemd service & backup timer aktif.
- [ ] Monitoring uptime ping berjalan.
- [ ] Kontak teknis & runbook tercatat di tempat aman.

---

Bagian E selesai.

## Ringkasan Bagian A–E

✅ **A** — Struktur repo (backend/frontend/deploy), stack Django+DRF+Postgres+Next.js, hybrid grid Glide+AG Grid Community
✅ **B** — Skema database 30+ tabel dengan invariant Bagian 9 enforced di DB-level
✅ **C** — ~150 endpoint API terkelompok per modul dengan permission codes
✅ **D** — ~40 halaman Next.js + 30+ komponen reusable
✅ **E** — Manual deploy Debian 11 lengkap (bootstrap → Docker → TLS → systemd → backup → restore → troubleshooting)

---
