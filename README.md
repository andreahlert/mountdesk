# MountDesk

[![Build RPM](https://github.com/andreahlert/mountdesk/actions/workflows/build.yml/badge.svg)](https://github.com/andreahlert/mountdesk/actions/workflows/build.yml)

Mount any cloud storage (Google Drive, OneDrive, Dropbox, SFTP, etc.) to your Linux desktop via [rclone](https://rclone.org/) FUSE mounts — with tray controls, file manager integration, and correct icons for Google Docs/Sheets/Slides.

## Features

- **Any rclone remote**: Configure any number of drives via YAML
- **Auto-mount on login**: Systemd user services generated automatically
- **System tray**: GTK tray app showing per-drive status and quick actions
- **File manager integration**: Nemo extension with colored emblems and context menu
- **Correct icons**: Google Docs/Sheets/Slides files show proper icons even when empty (rclone Google Doc exports)
- **"Open in Cloud"**: Right-click any file to open it in Google Drive web
- **Zero vendor lock-in**: Works with any cloud provider rclone supports (70+ backends)

## Installation

### Fedora / RHEL / CentOS Stream (RPM)

```bash
# From Fedora Copr (recommended)
sudo dnf copr enable andreahlert/mountdesk
sudo dnf install mountdesk
```

Or download the latest RPM from [Releases](https://github.com/andreahlert/mountdesk/releases).

### Dependencies

```bash
sudo dnf install rclone nemo-python python3-pyyaml libappindicator-gtk3 jq google-chrome-stable
```

> **Note**: `rclone` must be configured with your cloud provider(s) before running MountDesk. Run `rclone config` to set up OAuth.

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

  - name: "Servidor SFTP"
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
git clone https://github.com/andreahlert/mountdesk.git
cd mountdesk
sudo dnf install rpm-build
make rpm
sudo dnf install ./rpmbuild/RPMS/noarch/mountdesk-*.rpm
```

## Screenshots

*(Coming soon)*

## Supported Cloud Providers

Any provider supported by [rclone](https://rclone.org/):
- Google Drive (personal & shared drives)
- Dropbox
- OneDrive / SharePoint
- Amazon S3
- SFTP / SSH
- WebDAV
- Nextcloud
- And 60+ more

## License

MIT — Copyright (c) 2026 André Ahlert Junior
