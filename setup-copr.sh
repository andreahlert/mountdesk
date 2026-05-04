#!/bin/bash
# MountDesk - Fedora Copr Setup Script
# Run this after configuring your ~/.config/copr API token

set -e

COPR_CONFIG="$HOME/.config/copr"

if [[ ! -f "$COPR_CONFIG" ]]; then
    echo "ERROR: Copr API token not found."
    echo ""
    echo "Please go to https://copr.fedorainfracloud.org/api/"
    echo "and create ~/.config/copr with your login and token."
    echo ""
    echo "Example:"
    echo "  [copr-cli]"
    echo "  login = your-fas-username"
    echo "  token = your-api-token"
    echo "  copr_url = https://copr.fedorainfracloud.org"
    exit 1
fi

echo "=== MountDesk Copr Setup ==="
echo ""

# 1. Create project
echo "Step 1/3: Creating Copr project 'mountdesk'..."
copr-cli create mountdesk \
  --description "MountDesk - Generic cloud drive desktop integration via rclone FUSE" \
  --instructions "sudo dnf copr enable andreahlert/mountdesk && sudo dnf install mountdesk" \
  --enable-net off \
  --chroot fedora-43-x86_64 2>/dev/null || {
    echo "  Project may already exist, continuing..."
  }

# 2. Add GitHub source
echo ""
echo "Step 2/3: Adding GitHub source package..."
copr-cli add-package-scm mountdesk \
  --name mountdesk \
  --clone-url https://github.com/andreahlert/mountdesk.git \
  --subdir rpm \
  --spec mountdesk.spec \
  --scm-type git \
  --webhook-rebuild on 2>/dev/null || {
    echo "  Package may already exist, continuing..."
  }

# 3. Trigger build
echo ""
echo "Step 3/3: Triggering first build..."
copr-cli build-package mountdesk --name mountdesk

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Your Copr project: https://copr.fedorainfracloud.org/coprs/andreahlert/mountdesk/"
echo ""
echo "Users can now install with:"
echo "  sudo dnf copr enable andreahlert/mountdesk"
echo "  sudo dnf install mountdesk"
