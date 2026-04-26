#!/usr/bin/env bash
# Install Docker CE + Docker Compose plugin di Debian 11.
# Versi apt-default Debian terlalu lama, jadi ambil dari repo resmi Docker.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "[ERROR] Jalankan dengan sudo." >&2
  exit 1
fi

echo "[1/4] tambah GPG key & repo Docker..."
install -m 0755 -d /etc/apt/keyrings
if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
  curl -fsSL https://download.docker.com/linux/debian/gpg | \
    gpg --dearmor -o /etc/apt/keyrings/docker.gpg
fi
chmod a+r /etc/apt/keyrings/docker.gpg

cat > /etc/apt/sources.list.d/docker.list <<EOF
deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable
EOF

echo "[2/4] install Docker..."
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "[3/4] log rotation Docker (cegah disk penuh)..."
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<EOF
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "50m", "max-file": "5" },
  "default-address-pools": [{ "base": "10.20.0.0/16", "size": 24 }]
}
EOF
systemctl restart docker

echo "[4/4] tambah user 'rasmara' ke group docker..."
if id rasmara >/dev/null 2>&1; then
  usermod -aG docker rasmara
fi

echo ""
echo "[DONE] Docker terpasang."
docker --version
docker compose version
echo ""
echo "Logout dan login lagi sebagai 'rasmara' supaya group docker aktif:"
echo "    exit"
echo "    ssh rasmara@<IP_VPS>"
echo "lalu lanjut ke 02-app-bootstrap.sh."
