# MountDesk

[![Build RPM](https://github.com/mountdesk/mountdesk/actions/workflows/build.yml/badge.svg)](https://github.com/mountdesk/mountdesk/actions/workflows/build.yml)

Mount any cloud storage (Google Drive, OneDrive, Dropbox, SFTP, etc.) to your Linux desktop via [rclone](https://rclone.org/) FUSE mounts — with tray controls, file manager integration, and correct icons for Google Docs/Sheets/Slides.

## Features

- **Any rclone remote**: Configure any number of drives via YAML
- **Auto-mount on login**: Systemd user services generated automatically
- **System tray**: GTK tray app showing per-drive status
- **File manager integration**: Nemo extension with colored emblems
- **Correct icons**: Google Docs/Sheets/Slides files show proper icons even when empty (rclone Google Doc exports)
- **"Open in Cloud"**: Right-click any file to open it in Google Drive web

## Installation

### Fedora (RPM)

```bash
# Download latest RPM from Releases
sudo dnf install ./mountdesk-*.noarch.rpm

# Or from Fedora Copr (coming soon)
sudo dnf copr enable mountdesk/mountdesk
sudo dnf install mountdesk
```

### Dependencies

```bash
sudo dnf install rclone nemo-python python3-pyyaml libappindicator-gtk3 jq google-chrome-stable
```

## Quick Start

1. **Configure your drives**:

```bash
mkdir -p ~/.config/mountdesk
cp /usr/share/mountdesk/config.yaml.example ~/.config/mountdesk/config.yaml
$EDITOR ~/.config/mountdesk/config.yaml
```

Example `config.yaml`:

```yaml
drives:
  - name: "Meu Drive"
    remote: "gdrive"
    mountpoint: "~/Cloud/MeuDrive"

  - name: "Trabalho"
    remote: "gdrive-work"
    mountpoint: "~/Cloud/Trabalho"

  - name: "Servidor"
    remote: "sftp-server"
    mountpoint: "~/Cloud/Servidor"

settings:
  tray_refresh_interval: 5
  chrome: "google-chrome-stable"
```

2. **Run setup** (generates systemd services and starts everything):

```bash
/usr/lib/mountdesk/setup.sh
```

3. **Manage drives**: Edit `~/.config/mountdesk/config.yaml` and re-run `setup.sh`.

## Architecture

```
~/.config/mountdesk/config.yaml
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  mountdesk-tray │────▶│ systemd user    │
│  (GTK/AppInd)   │     │ services (auto  │
└─────────────────┘     │ generated)      │
         │              └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│ Nemo extension  │     │ rclone mount    │
│ (emblems/menu)  │     │ (FUSE)          │
└─────────────────┘     └─────────────────┘
```

## Building from Source

```bash
# Fedora
sudo dnf install rpm-build
make rpm
```

## License

MIT
