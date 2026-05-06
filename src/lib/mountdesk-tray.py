#!/usr/bin/env python3
"""
MountDesk Tray App — AppIndicator3/GTK3
Menu: abrir drives, sync, configurar, sair
"""

import os
import sys
import subprocess
import yaml
import re

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GObject, GLib

CONFIG_PATH = os.path.expanduser("~/.config/mountdesk/config.yaml")


def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f) or {"drives": [], "settings": {}}
    except Exception as e:
        return {"drives": [], "settings": {}}


def is_service_active(name):
    try:
        r = subprocess.run(["systemctl", "--user", "is-active", name],
                           capture_output=True, text=True, check=False)
        return r.returncode == 0
    except Exception:
        return False


def ensure_service(drive):
    # remote name is canonical service name (already prefixed `mountdesk-` and slugified)
    svc = drive["remote"]
    file_path = os.path.expanduser(f"~/.config/systemd/user/{svc}.service")
    mountpoint = os.path.expanduser(drive["mountpoint"])
    remote = drive["remote"]

    if not os.path.exists(file_path):
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
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(unit)
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "--user", "enable", svc], check=False)
        subprocess.run(["systemctl", "--user", "start", svc], check=False)
    return svc


class MountDeskTrayApp:
    def __init__(self):
        self.config = load_config()
        self.drives = self.config.get("drives", [])
        self.settings = self.config.get("settings", {})

        self.indicator = AppIndicator3.Indicator.new(
            "mountdesk", "mountdesk",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_title("MountDesk")

        self.menu = Gtk.Menu()
        self.indicator.set_menu(self.menu)
        self._build_menu()
        self._start_refresh()

    def _svc_name(self, drive):
        return drive["remote"]

    def _build_menu(self):
        # Título
        title = Gtk.MenuItem(label="MountDesk")
        title.set_sensitive(False)
        self.menu.append(title)
        self.menu.append(Gtk.SeparatorMenuItem())

        # Drives (status + click abre mountpoint)
        self.drive_items = []
        for drive in self.drives:
            ensure_service(drive)
            svc = self._svc_name(drive)
            active = is_service_active(svc)
            status = "🟢" if active else "🔴"
            item = Gtk.MenuItem(label=f"{status} {drive['name']}")
            item.connect("activate", self._open_drive, drive)
            self.menu.append(item)
            self.drive_items.append((item, drive, svc))

        self.menu.append(Gtk.SeparatorMenuItem())

        wizard = Gtk.MenuItem(label="⚙️ Configure")
        wizard.connect("activate", self._open_wizard)
        self.menu.append(wizard)

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self._quit)
        self.menu.append(quit_item)

        self.menu.show_all()

    def _open_drive(self, widget, drive):
        mp = os.path.expanduser(drive['mountpoint'])
        subprocess.Popen(["nemo", mp])

    def _open_wizard(self, widget):
        subprocess.Popen(["/usr/bin/python3", "/usr/lib/mountdesk/mountdesk-wizard.py"])

    def _quit(self, widget):
        Gtk.main_quit()

    def _start_refresh(self):
        interval = self.settings.get("tray_refresh_interval", 5)
        GLib.timeout_add_seconds(interval, self._refresh_status)

    def _refresh_status(self):
        for item, drive, svc in self.drive_items:
            active = is_service_active(svc)
            item.set_label(f"{'🟢' if active else '🔴'} {drive['name']}")
        return True


def main():
    app = MountDeskTrayApp()
    Gtk.main()


if __name__ == "__main__":
    main()
