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

# 2. Gerar services systemd para cada drive
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
    # systemd só aceita [a-z0-9-] em nomes de unidade
    safe_name = re.sub(r'[^a-z0-9-]', '', name.lower().replace(' ', '-'))
    service_name = f"mountdesk-{safe_name}"
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
  --vfs-cache-max-age 1h \\
  --vfs-cache-max-size 2G \\
  --vfs-read-chunk-size 16M \\
  --dir-cache-time 5m \\
  --poll-interval 1m \\
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
~/bin/mountdesk-fix-icons 2>/dev/null || true

# 5. Service do tray app
TRAY_SERVICE="$SYSTEMD_DIR/mountdesk-tray.service"
if [[ ! -f "$TRAY_SERVICE" ]]; then
    cat > "$TRAY_SERVICE" << 'EOF'
[Unit]
Description=MountDesk Tray App
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 %h/.local/lib/mountdesk/mountdesk-tray.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF
    systemctl --user daemon-reload
fi

echo ""
echo "Starting tray app..."
systemctl --user enable mountdesk-tray 2>/dev/null || true
systemctl --user start mountdesk-tray 2>/dev/null || true

echo ""
echo "=== Setup complete ==="
echo "MountDesk is running."
