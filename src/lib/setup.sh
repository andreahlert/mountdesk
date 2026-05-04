#!/bin/bash
# MountDesk - Setup Script
# Run this once to configure everything

set -e

echo "=== MountDesk Setup ==="
echo ""

CONFIG_DIR="$HOME/.config/mountdesk"
MIME_PACKAGES="$HOME/.local/share/mime/packages"
mkdir -p "$CONFIG_DIR" "$MIME_PACKAGES"

# 1. Ensure config exists
if [[ ! -f "$CONFIG_DIR/config.yaml" ]]; then
    cat > "$CONFIG_DIR/config.yaml" << 'EOF'
# MountDesk Configuration
# Add any rclone remote here to mount it automatically.

drives:
  # Example:
  # - name: "Meu Drive"
  #   remote: "gdrive"
  #   mountpoint: "~/GoogleDrive/MeuDrive"

settings:
  tray_refresh_interval: 5
  chrome: "google-chrome-stable"
  icons:
    sheets: "google-sheets"
    docs: "google-docs"
    slides: "google-slides"
EOF
    echo "✓ Created default config at $CONFIG_DIR/config.yaml"
    echo "  EDIT THIS FILE to add your rclone remotes and mount points."
fi

# 2. Ensure MIME overrides are registered
if [[ ! -f "$MIME_PACKAGES/override-rclone-empty.xml" ]]; then
    cat > "$MIME_PACKAGES/override-rclone-empty.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet">
    <glob weight="100" pattern="*.xlsx"/>
    <glob weight="100" pattern="*.XLSX"/>
  </mime-type>
  <mime-type type="application/vnd.openxmlformats-officedocument.wordprocessingml.document">
    <glob weight="100" pattern="*.docx"/>
    <glob weight="100" pattern="*.DOCX"/>
  </mime-type>
  <mime-type type="application/vnd.openxmlformats-officedocument.presentationml.presentation">
    <glob weight="100" pattern="*.pptx"/>
    <glob weight="100" pattern="*.PPTX"/>
  </mime-type>
  <mime-type type="application/vnd.oasis.opendocument.spreadsheet">
    <glob weight="100" pattern="*.ods"/>
    <glob weight="100" pattern="*.ODS"/>
  </mime-type>
  <mime-type type="application/vnd.oasis.opendocument.text">
    <glob weight="100" pattern="*.odt"/>
    <glob weight="100" pattern="*.ODT"/>
  </mime-type>
  <mime-type type="application/pdf">
    <glob weight="100" pattern="*.pdf"/>
    <glob weight="100" pattern="*.PDF"/>
  </mime-type>
  <mime-type type="image/png">
    <glob weight="100" pattern="*.png"/>
    <glob weight="100" pattern="*.PNG"/>
  </mime-type>
  <mime-type type="image/jpeg">
    <glob weight="100" pattern="*.jpg"/>
    <glob weight="100" pattern="*.jpeg"/>
    <glob weight="100" pattern="*.JPG"/>
    <glob weight="100" pattern="*.JPEG"/>
  </mime-type>
</mime-info>
EOF
    update-mime-database "$HOME/.local/share/mime"
    echo "✓ MIME overrides registered"
fi

# 3. Generate systemd services for each drive and ensure mount points exist
python3 << 'PYEOF'
import os, yaml, sys
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
    service_name = f"mountdesk-{name.lower().replace(' ', '-')}"
    service_file = os.path.join(systemd_dir, f"{service_name}.service")
    
    os.makedirs(mountpoint, exist_ok=True)
    
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
    print(f"✓ {service_name} configured -> {mountpoint}")

PYEOF

systemctl --user daemon-reload

# 4. Enable and start all mountdesk services
for svc in $(systemctl --user list-unit-files 'mountdesk-*.service' --no-legend 2>/dev/null | awk '{print $1}'); do
    systemctl --user enable "$svc" 2>/dev/null || true
    systemctl --user start "$svc" 2>/dev/null || true
    echo "✓ $svc enabled and started"
done

# 5. Fix icons
echo ""
echo "Fixing file icons..."
~/bin/mountdesk-fix-icons 2>/dev/null || true

# 6. Start tray app
echo ""
echo "Starting tray app..."
systemctl --user enable mountdesk-tray 2>/dev/null || true
systemctl --user start mountdesk-tray 2>/dev/null || true

echo ""
echo "=== Setup complete ==="
echo "MountDesk is now running."
echo ""
echo "Features:"
echo "  • Tray icon in GNOME top bar"
echo "  • Colored icons for Google Docs/Sheets/Slides files"
echo "  • Right-click on files → 'Abrir no Google Drive'"
echo "  • Auto-start on login"
echo ""
echo "To add/remove drives, edit:"
echo "  ~/.config/mountdesk/config.yaml"
echo "Then run:"
echo "  ~/.local/lib/mountdesk/setup.sh"
