#!/bin/bash
# MountDesk Setup Script
# Gera services systemd, monta drives, inicia tray app

set -e

echo "=== MountDesk Setup ==="
echo ""

CONFIG_DIR="$HOME/.config/mountdesk"
SYSTEMD_DIR="$HOME/.config/systemd/user"
mkdir -p "$CONFIG_DIR" "$SYSTEMD_DIR"

# 1. Verificar config
if [[ ! -f "$CONFIG_DIR/config.yaml" ]]; then
    echo "⚠ No config.yaml found. Run the wizard first:"
    echo "   ~/.local/lib/mountdesk/mountdesk-wizard.py"
    exit 1
fi

# 2. Sweep stale mountdesk drive services (keep tray)
for unit in "$SYSTEMD_DIR"/mountdesk-*.service; do
    [[ -f "$unit" ]] || continue
    base=$(basename "$unit" .service)
    [[ "$base" == "mountdesk-tray" ]] && continue
    systemctl --user stop "$base" 2>/dev/null || true
    systemctl --user disable "$base" 2>/dev/null || true
    rm -f "$unit"
done
systemctl --user daemon-reload

# 3. Gerar services systemd para cada drive
python3 << 'PYEOF'
import os, yaml, sys, re

config_path = os.path.expanduser("~/.config/mountdesk/config.yaml")
systemd_dir = os.path.expanduser("~/.config/systemd/user")
os.makedirs(systemd_dir, exist_ok=True)

try:
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
except Exception as e:
    print(f"Error reading config: {e}")
    sys.exit(1)

for drive in config.get("drives", []):
    name = drive["name"]
    remote = drive["remote"]
    mountpoint = os.path.expanduser(drive["mountpoint"])
    # remote name is already prefixed `mountdesk-` and slugified by wizard
    service_name = remote
    service_file = os.path.join(systemd_dir, f"{service_name}.service")
    
    if not os.path.isdir(mountpoint): os.makedirs(mountpoint, exist_ok=True)
    
    unit = f"""[Unit]
Description=MountDesk mount - {name}
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
ExecStart=/usr/bin/rclone mount {remote}: {mountpoint} \\
  --vfs-cache-mode full \\
  --vfs-cache-max-age 24h \\
  --vfs-cache-max-size 4G \\
  --vfs-read-chunk-size 16M \\
  --vfs-fast-fingerprint \\
  --dir-cache-time 24h \\
  --poll-interval 15s \\
  --attr-timeout 1s \\
  --no-modtime \\
  --allow-non-empty
ExecStop=/bin/fusermount -u {mountpoint}
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
"""
    with open(service_file, "w") as f:
        f.write(unit)
    print(f"✓ {service_name} -> {mountpoint}")

PYEOF

systemctl --user daemon-reload

# 3. Habilitar e iniciar todos os services mountdesk
for svc in $(systemctl --user list-unit-files 'mountdesk-*.service' --no-legend 2>/dev/null | awk '{print $1}'); do
    systemctl --user enable "$svc" 2>/dev/null || true
    systemctl --user start "$svc" 2>/dev/null || true
    echo "✓ $svc active"
done

# 4. Fix icons
echo ""
echo "Updating icons..."
/usr/bin/mountdesk-fix-icons 2>/dev/null || true

# 5. Register MIME handler for Google export formats (open in Chrome --app=)
HANDLER_DESKTOP="mountdesk-handler.desktop"
if [[ -f "/usr/share/applications/$HANDLER_DESKTOP" ]]; then
    for mime in \
        application/vnd.openxmlformats-officedocument.wordprocessingml.document \
        application/vnd.openxmlformats-officedocument.spreadsheetml.sheet \
        application/vnd.openxmlformats-officedocument.presentationml.presentation \
        application/vnd.oasis.opendocument.text \
        application/vnd.oasis.opendocument.spreadsheet \
        application/vnd.oasis.opendocument.presentation \
        text/csv ; do
        xdg-mime default "$HANDLER_DESKTOP" "$mime" 2>/dev/null || true
    done
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

# 6. Service do tray app (always overwrite to fix stale paths from earlier installs)
TRAY_SERVICE="$SYSTEMD_DIR/mountdesk-tray.service"
cat > "$TRAY_SERVICE" << 'EOF'
[Unit]
Description=MountDesk Tray App
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/lib/mountdesk/mountdesk-tray.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload

echo ""
echo "Starting tray app..."
systemctl --user enable mountdesk-tray 2>/dev/null || true
systemctl --user restart mountdesk-tray 2>/dev/null || true

echo ""
echo "=== Setup complete ==="
echo "MountDesk is running."
