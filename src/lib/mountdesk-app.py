#!/usr/bin/env python3
"""
MountDesk Desktop App — Janela principal GTK4
Lista drives, status, ações. Integra com tray app.
"""

import os
import sys
import subprocess
import yaml
import threading

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio

CONFIG_PATH = os.path.expanduser("~/.config/mountdesk/config.yaml")
MOUNTDESK_ICON = "drive-harddisk"


def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f) or {"drives": [], "settings": {}}
    except Exception:
        return {"drives": [], "settings": {}}


def is_service_active(name):
    try:
        r = subprocess.run(["systemctl", "--user", "is-active", name],
                           capture_output=True, text=True, check=False)
        return r.returncode == 0
    except Exception:
        return False


def svc_name(drive_name):
    import re
    safe = re.sub(r'[^a-z0-9-]', '', drive_name.lower().replace(' ', '-'))
    return f"mountdesk-{safe}"


class DriveRow(Gtk.Box):
    def __init__(self, drive, app_window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.drive = drive
        self.app_window = app_window
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(12)
        self.set_margin_end(12)

        # Card frame
        self.card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.card.add_css_class("card")
        self.card.set_margin_top(4)
        self.card.set_margin_bottom(4)

        # Top row: icon + name + status
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        top.set_margin_top(12)
        top.set_margin_start(12)
        top.set_margin_end(12)

        icon = Gtk.Image.new_from_icon_name("folder-remote")
        icon.set_pixel_size(32)
        top.append(icon)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info.set_hexpand(True)

        self.name_lbl = Gtk.Label()
        self.name_lbl.set_markup(f"<b>{drive['name']}</b>")
        self.name_lbl.set_halign(Gtk.Align.START)
        info.append(self.name_lbl)

        self.path_lbl = Gtk.Label(label=drive['mountpoint'])
        self.path_lbl.add_css_class("caption")
        self.path_lbl.set_halign(Gtk.Align.START)
        info.append(self.path_lbl)

        top.append(info)

        self.status_lbl = Gtk.Label()
        self.status_lbl.set_halign(Gtk.Align.END)
        top.append(self.status_lbl)

        self.card.append(top)

        # Button row
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_bottom(12)
        btn_box.set_margin_start(12)
        btn_box.set_margin_end(12)

        open_btn = Gtk.Button(label="📂 Open folder")
        open_btn.connect("clicked", self._on_open_folder)
        btn_box.append(open_btn)

        browser_btn = Gtk.Button(label="🌐 Open in Drive")
        browser_btn.add_css_class("suggested-action")
        browser_btn.connect("clicked", self._on_open_browser)
        btn_box.append(browser_btn)

        self.card.append(btn_box)
        self.append(self.card)

        self._update_status()

    def _update_status(self):
        active = is_service_active(svc_name(self.drive['name']))
        if active:
            self.status_lbl.set_markup("<span color='#26a269'>🟢 Mounted</span>")
        else:
            self.status_lbl.set_markup("<span color='#e01b24'>🔴 Unmounted</span>")

    def _on_open_folder(self, btn):
        mp = os.path.expanduser(self.drive['mountpoint'])
        subprocess.Popen(["nemo", mp])

    def _on_open_browser(self, btn):
        subprocess.Popen([
            os.path.expanduser("~/bin/mountdesk-open-link"),
            os.path.expanduser(self.drive['mountpoint'])
        ])


class MountDeskMainWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("MountDesk")
        self.set_default_size(520, 400)

        # Header
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="MountDesk"))

        menu_btn = Gtk.MenuButton()
        menu_btn.set_icon_name("open-menu-symbolic")
        header.pack_end(menu_btn)

        # Content
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content.append(header)

        # Scrollable list
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.add_css_class("boxed-list")

        scroll.set_child(self.list_box)
        self.content.append(scroll)

        # Bottom action bar
        action_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        action_bar.set_margin_top(12)
        action_bar.set_margin_bottom(12)
        action_bar.set_margin_start(12)
        action_bar.set_margin_end(12)
        action_bar.set_halign(Gtk.Align.CENTER)

        sync_btn = Gtk.Button(label="🔄 Sync icons")
        sync_btn.connect("clicked", self._on_sync)
        action_bar.append(sync_btn)

        config_btn = Gtk.Button(label="⚙️ Configure")
        config_btn.add_css_class("suggested-action")
        config_btn.connect("clicked", self._on_config)
        action_bar.append(config_btn)

        quit_btn = Gtk.Button(label="Sair")
        quit_btn.connect("clicked", lambda _: self.close())
        action_bar.append(quit_btn)

        self.content.append(action_bar)

        self.set_content(self.content)
        self._build_drive_list()
        self._start_refresh()

    def _build_drive_list(self):
        # Clear
        while True:
            row = self.list_box.get_first_child()
            if row is None:
                break
            self.list_box.remove(row)

        config = load_config()
        drives = config.get("drives", [])

        if not drives:
            empty = Gtk.Label()
            empty.set_markup("<span color='#888' size='large'>No drives configured</span>\n\n"
                           "Click <b>Configure</b> to add one.")
            empty.set_margin_top(48)
            empty.set_vexpand(True)
            self.list_box.append(empty)
            return

        for drive in drives:
            row_widget = DriveRow(drive, self)
            self.list_box.append(row_widget)

    def _on_sync(self, btn):
        def do_sync():
            subprocess.run([os.path.expanduser("~/bin/mountdesk-fix-icons")],
                          capture_output=True, check=False)
            GLib.idle_add(lambda: self._show_toast("Icons synced"))
        t = threading.Thread(target=do_sync)
        t.daemon = True
        t.start()

    def _on_config(self, btn):
        subprocess.Popen([
            "/usr/bin/python3",
            os.path.expanduser("~/.local/lib/mountdesk/mountdesk-wizard.py")
        ])

    def _show_toast(self, msg):
        # Simple toast via dialog
        dialog = Adw.MessageDialog.new(self, None, msg)
        dialog.add_response("ok", "OK")
        dialog.present()

    def _start_refresh(self):
        GLib.timeout_add_seconds(5, self._refresh_status)

    def _refresh_status(self):
        # Rebuild to refresh status (simple approach)
        self._build_drive_list()
        return True


class MountDeskApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.mountdesk.app",
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        win = MountDeskMainWindow(app)
        win.present()


def main():
    app = MountDeskApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
