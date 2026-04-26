#!/usr/bin/env bash
# Install systemd service utk auto-start RASMARA + backup harian.
# Path repo & user di-derive otomatis dari lokasi script & USER aktif.
#
# Pemakaian:
#   sudo bash deploy/debian11/install-systemd.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "[ERROR] Jalankan dengan sudo." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
TARGET_USER="${TARGET_USER:-${SUDO_USER:-$USER}}"

echo "[*] Repo:  $REPO_DIR"
echo "[*] User:  $TARGET_USER"

# Render template -> /etc/systemd/system/
for tpl in "$SCRIPT_DIR"/systemd/*.template; do
  base=$(basename "$tpl" .template)
  out="/etc/systemd/system/$base"
  echo "[*] Install: $out"
  sed \
    -e "s|__REPO_DIR__|$REPO_DIR|g" \
    -e "s|__USER__|$TARGET_USER|g" \
    "$tpl" > "$out"
  chmod 644 "$out"
done

# Copy timer file apa adanya (tidak butuh templating)
cp "$SCRIPT_DIR/systemd/rasmara-backup.timer" /etc/systemd/system/
chmod 644 /etc/systemd/system/rasmara-backup.timer

systemctl daemon-reload

# Enable & start
systemctl enable --now rasmara.service
systemctl enable --now rasmara-backup.timer

echo ""
echo "[DONE] Systemd terpasang."
echo "  rasmara.service       -> auto-up stack saat boot."
echo "  rasmara-backup.timer  -> backup harian 02:00 WIB."
echo ""
echo "Cek status:"
echo "    systemctl status rasmara.service"
echo "    systemctl list-timers | grep rasmara"
