#!/bin/bash
# MountDesk Migration Script
# Safely removes SolGreen Drive artifacts and activates MountDesk

set -e

echo "=== MountDesk Migration ==="
echo ""
echo "This will:"
echo "  1. Stop and disable SolGreen services"
echo "  2. Remove SolGreen files"
echo "  3. Preserve your rclone config (OAuth tokens)"
echo "  4. Activate MountDesk"
echo ""
read -p "Continue? [y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Step 1/4: Stopping SolGreen services..."
for svc in solgreen-drive-tray rclone-controladoria rclone-financeiro rclone-solgreen rclone-gdrive rclone-meudrive; do
    systemctl --user stop "$svc" 2>/dev/null || true
    systemctl --user disable "$svc" 2>/dev/null || true
    echo "  ✓ Stopped $svc"
done
systemctl --user daemon-reload

echo ""
echo "Step 2/4: Removing SolGreen files..."

# Scripts
rm -f ~/bin/open-gdrive-link ~/bin/google-drive-app ~/bin/google-drive-native-app ~/bin/fix-rclone-icons

# Tray app
rm -rf ~/.local/lib/solgreen-drive

# Nemo extension
rm -f ~/.local/share/nemo-python/extensions/solgreen-drive-nemo.py

# Desktop entries
rm -f ~/.local/share/applications/solgreen-drive.desktop
rm -f ~/.local/share/applications/google-sheets-native.desktop
rm -f ~/.local/share/applications/google-docs-native.desktop
rm -f ~/.local/share/applications/google-slides-native.desktop

# Systemd services
rm -f ~/.config/systemd/user/solgreen-drive-tray.service
rm -f ~/.config/systemd/user/rclone-controladoria.service
rm -f ~/.config/systemd/user/rclone-financeiro.service
rm -f ~/.config/systemd/user/rclone-solgreen.service
rm -f ~/.config/systemd/user/rclone-gdrive.service
rm -f ~/.config/systemd/user/rclone-meudrive.service

# Update desktop database
update-desktop-database ~/.local/share/applications 2>/dev/null || true

echo "  ✓ SolGreen files removed"

echo ""
echo "Step 3/4: Migrating config to MountDesk..."

mkdir -p ~/.config/mountdesk

# Create MountDesk config if it doesn't exist
if [[ ! -f ~/.config/mountdesk/config.yaml ]]; then
    cat > ~/.config/mountdesk/config.yaml << 'EOF'
# MountDesk Configuration
# Add any rclone remote here to mount it automatically.

drives:
  - name: "Controladoria"
    remote: "gdrive-controladoria"
    mountpoint: "~/GoogleDrive/Controladoria"

  - name: "Financeiro"
    remote: "gdrive-financeiro"
    mountpoint: "~/GoogleDrive/Financeiro"

  - name: "Solgreen"
    remote: "gdrive-solgreen"
    mountpoint: "~/GoogleDrive/Solgreen"

  - name: "MeuDrive"
    remote: "gdrive"
    mountpoint: "~/GoogleDrive/MeuDrive"

settings:
  tray_refresh_interval: 5
  chrome: "google-chrome-stable"
  icons:
    sheets: "google-sheets"
    docs: "google-docs"
    slides: "google-slides"
EOF
    echo "  ✓ Created MountDesk config with your SolGreen drives"
else
    echo "  ✓ MountDesk config already exists (kept as-is)"
fi

echo ""
echo "Step 4/4: Activating MountDesk..."

# Ensure binaries are executable
chmod +x ~/bin/mountdesk-open-link ~/bin/mountdesk-fix-icons
chmod +x ~/.local/lib/mountdesk/*.py ~/.local/lib/mountdesk/*.sh

# Run MountDesk setup
~/.local/lib/mountdesk/setup.sh

echo ""
echo "=== Migration Complete ==="
echo ""
echo "MountDesk is now active."
echo ""
echo "To add/remove drives, edit:"
echo "  ~/.config/mountdesk/config.yaml"
echo "Then run:"
echo "  ~/.local/lib/mountdesk/setup.sh"
echo ""
echo "Your rclone config is preserved at:"
echo "  ~/.config/rclone/rclone.conf"
