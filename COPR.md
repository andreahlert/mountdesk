# Fedora Copr Setup Guide

## Goal

Publish MountDesk on [Fedora Copr](https://copr.fedorainfracloud.org/) so users can install with:

```bash
sudo dnf copr enable andreahlert/mountdesk
sudo dnf install mountdesk
```

---

## Step 1: Get API Token

1. Go to https://copr.fedorainfracloud.org/api/
2. Click **"Login"** (uses Fedora Account System)
3. Copy the **API token** shown on the page
4. Save it to `~/.config/copr`:

```bash
mkdir -p ~/.config
cat > ~/.config/copr << 'EOF'
[copr-cli]
login = YOUR_LOGIN_HERE
token = YOUR_TOKEN_HERE
copr_url = https://copr.fedorainfracloud.org
EOF
chmod 600 ~/.config/copr
```

---

## Step 2: Create Copr Project

```bash
copr-cli create mountdesk \
  --description "MountDesk - Generic cloud drive desktop integration via rclone FUSE" \
  --instructions "sudo dnf copr enable andreahlert/mountdesk && sudo dnf install mountdesk" \
  --enable-net off \
  --chroot fedora-43-x86_64
```

---

## Step 3: Add GitHub Source

```bash
copr-cli add-package-scm mountdesk \
  --name mountdesk \
  --clone-url https://github.com/andreahlert/mountdesk.git \
  --subdir rpm \
  --spec mountdesk.spec \
  --scm-type git \
  --webhook-rebuild on
```

---

## Step 4: Trigger First Build

```bash
copr-cli build-package mountdesk --name mountdesk
```

---

## Alternative: Manual Upload

If you prefer not to use GitHub integration, upload the RPM directly:

```bash
copr-cli build mountdesk ~/rpmbuild/RPMS/noarch/mountdesk-1.0.0-1.fc43.noarch.rpm
```

---

## After Publishing

Update the README with the Copr badge:

```markdown
[![Copr](https://copr.fedorainfracloud.org/coprs/andreahlert/mountdesk/package/mountdesk/status_image/last_build.png)](https://copr.fedorainfracloud.org/coprs/andreahlert/mountdesk/)
```
