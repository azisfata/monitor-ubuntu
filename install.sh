#!/usr/bin/env bash
# Monitor Ubuntu — portable installer (Linux, systemd --user, stdlib only).
# Usage:
#   git clone https://github.com/azisfata/monitor-ubuntu.git ~/monitor
#   cd ~/monitor && ./install.sh
# Env overrides (non-interactive):
#   MONITOR_PORT=8899 MONITOR_USER=admin MONITOR_PASS=secret ./install.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
SVC_DIR="$HOME/.config/systemd/user"
CONF="$APP_DIR/monitor.conf.json"
PORT="${MONITOR_PORT:-${PORT:-8899}}"
MUSER="${MONITOR_USER:-admin}"
MPASS="${MONITOR_PASS:-}"

echo "==> Monitor Ubuntu installer"
echo "    dir : $APP_DIR"
echo "    port: $PORT"

command -v python3 >/dev/null || { echo "butuh python3"; exit 1; }

# 1. config (jangan timpa jika sudah ada)
if [ ! -f "$CONF" ]; then
  # Generate via python3 supaya password dengan karakter khusus (" \ & dll)
  # tetap menghasilkan JSON yang valid.
  MONITOR_PORT="$PORT" MONITOR_USER="$MUSER" MONITOR_PASS="$MPASS" \
  CONF_PATH="$CONF" python3 <<'PY'
import json, os, secrets

conf_path = os.environ["CONF_PATH"]
port = int(os.environ.get("MONITOR_PORT") or 8899)
user = os.environ.get("MONITOR_USER") or "admin"
pw = os.environ.get("MONITOR_PASS") or ""
if not pw:
    pw = secrets.token_urlsafe(12)

cfg = {
    "port": port,
    "title": "server",
    "users": {user: pw},
    "web": [],
    "known": {},
    "hide_ports": [20241],
    "infra_skip_apps": [22, 53, 631, 3389],
    "max_port": 32768,
    "systemd_units": [],
    "probe_timeout": 1,
    "snapshot_ttl": 2.0,
    "docker_all": False,
    "alert": {
        "interval": 300,
        "cooldown": 3600,
        "ram_threshold": 90,
        "disk_threshold": 90,
        "wa_admin": "",
        "wa_bridge": "http://127.0.0.1:3105/send",
        "wa_env_file": "~/.hermes/.env",
    },
}
tmp = conf_path + ".tmp"
with open(tmp, "w") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")
os.replace(tmp, conf_path)
os.chmod(conf_path, 0o600)
PY
  # Ambil password yang di-generate (kalau ada) supaya bisa ditampilkan sekali.
  if [ -z "$MPASS" ]; then
    MPASS="$(CONF="$CONF" MONITOR_USER="$MUSER" python3 -c 'import json,os;print(json.load(open(os.environ["CONF"]))["users"][os.environ["MONITOR_USER"]])' 2>/dev/null || true)"
  fi
  echo "    config dibuat: $CONF (user: $MUSER)"
  echo "    password    : $MPASS  <- simpan / ganti sekarang!"
else
  echo "    config ada, dilewati: $CONF"
fi

# 2. CLI symlink
mkdir -p "$BIN_DIR"
ln -sf "$APP_DIR/cli.py" "$BIN_DIR/monitor"
chmod +x "$APP_DIR/cli.py" "$APP_DIR/srv.py" "$APP_DIR/install.sh"
echo "    CLI: $BIN_DIR/monitor"

# 3. systemd user service (portable: pakai HOME/USER aktual)
mkdir -p "$SVC_DIR"
cat > "$SVC_DIR/monitor.service" <<EOF
[Unit]
Description=Monitor Ubuntu Dashboard (srv.py)
After=network-online.target
Wants=network-online.target
StartLimitBurst=5
StartLimitIntervalSec=60

[Service]
Type=simple
ExecStart=/usr/bin/python3 $APP_DIR/srv.py
WorkingDirectory=$APP_DIR
Restart=always
RestartSec=5
TimeoutStopSec=15
Environment=PORT=$PORT
Environment=PATH=/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin
Environment=HOME=$HOME

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now monitor.service

# 3b. linger: tanpa ini systemd --user ikut mati saat logout/reboot.
if loginctl show-user "$(id -un)" -p Linger 2>/dev/null | grep -q 'Linger=yes'; then
  echo "    linger: aktif"
elif command -v loginctl >/dev/null; then
  echo "    linger: belum aktif — masukkan:"
  echo "            sudo loginctl enable-linger $(id -un)"
  echo "          (tanpa ini service berhenti saat logout/reboot)"
fi
sleep 3
systemctl --user status monitor.service --no-pager -l | head -12

echo ""
echo "==> Selesai."
echo "    Dashboard: http://<IP-LAN-atau-Tailscale>:$PORT"
echo "    CLI      : monitor"
echo "    Config   : $CONF (atau env MONITOR_USER/MONITOR_PASS/MONITOR_PORT)"
echo "    Log      : journalctl --user -u monitor -f"
