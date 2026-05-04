#!/usr/bin/env python3
"""
MountDesk - Generic Google Drive desktop integration tray app.
Reads drive configuration from ~/.config/mountdesk/config.yaml
"""

import os
import sys
import subprocess
import yaml
import time
import threading

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GObject, GLib

CONFIG_PATH = os.path.expanduser("~/.config/mountdesk/config.yaml")
SYSTEMD_USER_DIR = os.path.expanduser("~/.config/systemd/user")


def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f) or {"drives": [], "settings": {}}
    except Exception as e:
        print(f"Failed to load config: {e}")
        return {"drives": [], "settings": {}}


def is_service_active(service_name):
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", service_name],
            capture_output=True, text=True, check=False
        )
        return result.returncode == 0
    except Exception:
        return False


def ensure_service(drive):
    """Generate and enable systemd service for a drive if not exists."""
    service_name = f"mountdesk-{drive['name'].lower().replace(' ', '-')}"
    service_file = os.path.join(SYSTEMD_USER_DIR, f"{service_name}.service")
    mountpoint = os.path.expanduser(drive['mountpoint'])
    remote = drive['remote']

    if not os.path.exists(service_file):
        unit = f"""[Unit]
Description=MountDesk mount - {drive['name']}
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
        os.makedirs(SYSTEMD_USER_DIR, exist_ok=True)
        with open(service_file, 'w') as f:
            f.write(unit)
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "--user", "enable", service_name], check=False)
        subprocess.run(["systemctl", "--user", "start", service_name], check=False)
    return service_name


class MountDeskTrayApp:
    def __init__(self):
        self.config = load_config()
        self.drives = self.config.get("drives", [])
        self.settings = self.config.get("settings", {})

        self.indicator = AppIndicator3.Indicator.new(
            "mountdesk",
            "drive-harddisk",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_title("MountDesk")

        self.menu = Gtk.Menu()
        self.indicator.set_menu(self.menu)

        self._build_menu()
        self._start_refresh()

    def _service_name(self, drive):
        return f"mountdesk-{drive['name'].lower().replace(' ', '-')}"

    def _build_menu(self):
        # Title
        title_item = Gtk.MenuItem(label="MountDesk")
        title_item.set_sensitive(False)
        self.menu.append(title_item)

        sep = Gtk.SeparatorMenuItem()
        self.menu.append(sep)

        self.drive_items = []
        for drive in self.drives:
            ensure_service(drive)
            svc = self._service_name(drive)
            active = is_service_active(svc)
            status = "🟢" if active else "🔴"
            item = Gtk.MenuItem(label=f"{status} {drive['name']}")
            item.connect("activate", self._open_drive, drive)
            self.menu.append(item)
            self.drive_items.append((item, drive, svc))

        sep2 = Gtk.SeparatorMenuItem()
        self.menu.append(sep2)

        # Actions
        sync_item = Gtk.MenuItem(label="🔄 Sync / Refresh Icons")
        sync_item.connect("activate", self._sync_all)
        self.menu.append(sync_item)

        config_item = Gtk.MenuItem(label="⚙️ Open Config")
        config_item.connect("activate", self._open_config)
        self.menu.append(config_item)

        sep3 = Gtk.SeparatorMenuItem()
        self.menu.append(sep3)

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self._quit)
        self.menu.append(quit_item)

        self.menu.show_all()

    def _open_drive(self, widget, drive):
        mountpoint = os.path.expanduser(drive['mountpoint'])
        subprocess.Popen(["nemo", mountpoint])

    def _sync_all(self, widget):
        subprocess.Popen([os.path.expanduser("~/bin/mountdesk-fix-icons")])
        # Refresh menu
        for item, drive, svc in self.drive_items:
            active = is_service_active(svc)
            status = "🟢" if active else "🔴"
            item.set_label(f"{status} {drive['name']}")

    def _open_config(self, widget):
        subprocess.Popen(["xdg-open", CONFIG_PATH])

    def _quit(self, widget):
        Gtk.main_quit()

    def _start_refresh(self):
        interval = self.settings.get("tray_refresh_interval", 5)
        GLib.timeout_add_seconds(interval, self._refresh_status)

    def _refresh_status(self):
        for item, drive, svc in self.drive_items:
            active = is_service_active(svc)
            status = "🟢" if active else "🔴"
            item.set_label(f"{status} {drive['name']}")
        return True


def main():
    app = MountDeskTrayApp()
    Gtk.main()


if __name__ == "__main__":
    main()
