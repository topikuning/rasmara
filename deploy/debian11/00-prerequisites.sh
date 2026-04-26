#!/usr/bin/env bash
# Bootstrap awal VPS Debian 11 untuk RASMARA.
# Harus dijalankan sebagai root.
#
# Yang dilakukan:
#   - apt update & upgrade
#   - install paket dasar
#   - buat user 'rasmara' dengan sudo + SSH key
#   - hardening SSH (disable root login, password auth)
#   - firewall ufw (22, 80, 443)
#   - fail2ban
#   - swap 4GB
#   - auto security update
#   - timezone Asia/Jakarta
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "[ERROR] Script ini harus dijalankan sebagai root." >&2
  exit 1
fi

if ! grep -qi "Debian GNU/Linux 11" /etc/os-release 2>/dev/null; then
  echo "[WARN] Sistem bukan Debian 11. Lanjut atas tanggung jawab sendiri."
  read -rp "Lanjut? [y/N] " ans
  [[ "${ans,,}" == "y" ]] || exit 1
fi

echo "[1/8] apt update & upgrade..."
export DEBIAN_FRONTEND=noninteractive
apt update
apt upgrade -y

echo "[2/8] install paket dasar..."
apt install -y curl wget git ufw fail2ban unattended-upgrades \
    ca-certificates gnupg lsb-release htop tmux rsync sudo \
    apt-transport-https software-properties-common

echo "[3/8] buat user 'rasmara' (jika belum ada)..."
if ! id rasmara >/dev/null 2>&1; then
  adduser --disabled-password --gecos "" rasmara
  usermod -aG sudo rasmara
  # password-less sudo (opsional; aman karena akses via SSH key only)
  echo "rasmara ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/rasmara
  chmod 440 /etc/sudoers.d/rasmara
fi

echo "[3.1] copy SSH authorized_keys ke user rasmara..."
mkdir -p /home/rasmara/.ssh
if [[ -f /root/.ssh/authorized_keys ]]; then
  cp /root/.ssh/authorized_keys /home/rasmara/.ssh/authorized_keys
fi
chown -R rasmara:rasmara /home/rasmara/.ssh
chmod 700 /home/rasmara/.ssh
[[ -f /home/rasmara/.ssh/authorized_keys ]] && chmod 600 /home/rasmara/.ssh/authorized_keys || true

echo "[4/8] hardening SSH..."
SSHD=/etc/ssh/sshd_config
sed -i -E 's/^#?PermitRootLogin.*/PermitRootLogin no/' "$SSHD"
sed -i -E 's/^#?PasswordAuthentication.*/PasswordAuthentication no/' "$SSHD"
sed -i -E 's/^#?KbdInteractiveAuthentication.*/KbdInteractiveAuthentication no/' "$SSHD"
sed -i -E 's/^#?ChallengeResponseAuthentication.*/ChallengeResponseAuthentication no/' "$SSHD"
sed -i -E 's/^#?UsePAM.*/UsePAM yes/' "$SSHD"
systemctl reload ssh || systemctl reload sshd || true

echo "[5/8] firewall ufw..."
ufw default deny incoming || true
ufw default allow outgoing || true
ufw allow 22/tcp comment "SSH" || true
ufw allow 80/tcp comment "HTTP" || true
ufw allow 443/tcp comment "HTTPS" || true
ufw --force enable

echo "[6/8] fail2ban..."
systemctl enable --now fail2ban

echo "[6.1] auto security update..."
dpkg-reconfigure -f noninteractive unattended-upgrades || true

echo "[7/8] swap 4GB (jika belum ada)..."
if ! swapon --show | grep -q '/swapfile'; then
  fallocate -l 4G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  if ! grep -q '/swapfile' /etc/fstab; then
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
  fi
  echo 'vm.swappiness=10' > /etc/sysctl.d/99-swappiness.conf
  sysctl -p /etc/sysctl.d/99-swappiness.conf
fi

echo "[8/8] timezone Asia/Jakarta..."
timedatectl set-timezone Asia/Jakarta

echo ""
echo "[DONE] Bootstrap selesai."
echo "Login ulang sebagai user 'rasmara':"
echo "    ssh rasmara@<IP_VPS>"
echo "lalu jalankan: sudo bash deploy/debian11/01-docker.sh"
