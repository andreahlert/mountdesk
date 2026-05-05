#!/usr/bin/env python3
"""
MountDesk Setup Wizard — 100% GUI, zero texto.
Fluxo: Boas-vindas → OAuth Google → Selecionar Drives → Configurar Montagens → Aplicar → Pronto
"""

import os
import sys
import subprocess
import yaml
import threading
import json
import time
import logging
import webbrowser

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

# Logging para debug
LOG_PATH = "/tmp/mountdesk-wizard.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, mode='w'),
        logging.StreamHandler(sys.stderr)
    ]
)
log = logging.getLogger("mountdesk-wizard")

# Lazy imports Google
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    _HAS_GOOGLE = True
except ImportError as e:
    log.error("Google libs not installed: %s", e)
    _HAS_GOOGLE = False

CONFIG_DIR = os.path.expanduser("~/.config/mountdesk")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.yaml")
RCLONE_CONFIG = os.path.expanduser("~/.config/rclone/rclone.conf")
MOUNT_BASE = os.path.expanduser("~/GoogleDrive")

# Rclone's public client ID (no secret needed from user)
RCLONE_CLIENT_ID = "202264815644.apps.googleusercontent.com"
RCLONE_CLIENT_SECRET = "X4Z3ca8xfWDb1Voo-F9a7ZxJ"
SCOPES = ['https://www.googleapis.com/auth/drive']


class WizardWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("MountDesk")
        self.set_default_size(700, 580)
        self.creds = None
        self.drives = []
        self.selected_drives = []
        self.drive_check_rows = []
        self._cancel_oauth = False
        self._oauth_thread = None

        self.stack = Adw.ViewStack()
        self.set_content(self.stack)

        self.stack.add_named(self._page_welcome(), "welcome")
        self.stack.add_named(self._page_oauth(),   "oauth")
        self.stack.add_named(self._page_drives(),  "drives")
        self.stack.add_named(self._page_mounts(),  "mounts")
        self.stack.add_named(self._page_finish(),  "finish")

        self.stack.set_visible_child_name("welcome")
        log.info("Wizard initialized")

    # ---------- Páginas ----------
    def _page_welcome(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        box.set_margin_top(48); box.set_margin_bottom(48)
        box.set_margin_start(48); box.set_margin_end(48)
        box.set_valign(Gtk.Align.CENTER)

        img = Gtk.Image.new_from_icon_name("mountdesk")
        img.set_pixel_size(96)
        box.append(img)

        box.append(self._title("MountDesk", "xx-large"))
        box.append(self._body("Mount your Google Drives on the desktop without editing any files."))

        feats = Gtk.Label()
        feats.set_wrap(True)
        feats.set_markup(
            "• One-click Google login\n"
            "• Select drives on screen\n"
            "• Auto-configures mounts\n"
            "• Google icons in file manager"
        )
        feats.set_margin_top(12)
        box.append(feats)

        btn = Gtk.Button(label="Connect to Google Drive")
        btn.add_css_class("suggested-action")
        btn.add_css_class("pill")
        btn.set_halign(Gtk.Align.CENTER)
        btn.set_margin_top(24)
        btn.connect("clicked", lambda _: self.stack.set_visible_child_name("oauth"))
        box.append(btn)
        return box

    def _page_oauth(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(40); box.set_margin_bottom(40)
        box.set_margin_start(40); box.set_margin_end(40)
        box.set_valign(Gtk.Align.CENTER)

        box.append(self._title("Connecting to Google", "x-large"))

        self.oauth_status = self._body("Click the button below to open your browser.")
        box.append(self.oauth_status)

        self.oauth_spinner = Gtk.Spinner()
        self.oauth_spinner.set_visible(False)
        box.append(self.oauth_spinner)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER)
        btn_box.set_margin_top(16)

        self.oauth_btn = Gtk.Button(label="Open browser and authenticate")
        self.oauth_btn.add_css_class("suggested-action")
        self.oauth_btn.add_css_class("pill")
        self.oauth_btn.connect("clicked", self._on_oauth_start)
        btn_box.append(self.oauth_btn)

        self.oauth_cancel_btn = Gtk.Button(label="Cancelar")
        self.oauth_cancel_btn.set_sensitive(False)
        self.oauth_cancel_btn.connect("clicked", self._on_oauth_cancel)
        btn_box.append(self.oauth_cancel_btn)

        box.append(btn_box)

        back = Gtk.Button(label="← Voltar")
        back.set_halign(Gtk.Align.CENTER)
        back.connect("clicked", lambda _: self.stack.set_visible_child_name("welcome"))
        box.append(back)
        return box

    def _page_drives(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(24); box.set_margin_bottom(24)
        box.set_margin_start(24); box.set_margin_end(24)

        box.append(self._title("Select drives", "x-large"))
        self.drives_label = self._body("Carregando...")
        box.append(self.drives_label)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        self.drives_box = Gtk.ListBox()
        self.drives_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.drives_box.add_css_class("boxed-list")
        scroll.set_child(self.drives_box)
        box.append(scroll)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER); btn_box.set_margin_top(24)

        back = Gtk.Button(label="Voltar")
        back.connect("clicked", lambda _: self.stack.set_visible_child_name("oauth"))
        btn_box.append(back)

        next_btn = Gtk.Button(label="Continue →")
        next_btn.add_css_class("suggested-action")
        next_btn.connect("clicked", self._on_drives_next)
        btn_box.append(next_btn)
        box.append(btn_box)
        return box

    def _page_mounts(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(24); box.set_margin_bottom(24)
        box.set_margin_start(24); box.set_margin_end(24)

        box.append(self._title("Where to mount?", "x-large"))
        box.append(self._body("Each drive will be mounted in a folder. You can change the paths."))

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        self.mounts_box = Gtk.ListBox()
        self.mounts_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.mounts_box.add_css_class("boxed-list")
        scroll.set_child(self.mounts_box)
        box.append(scroll)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER); btn_box.set_margin_top(24)

        back = Gtk.Button(label="Voltar")
        back.connect("clicked", lambda _: self.stack.set_visible_child_name("drives"))
        btn_box.append(back)

        finish_btn = Gtk.Button(label="✓ Apply and Mount")
        finish_btn.add_css_class("suggested-action")
        finish_btn.connect("clicked", self._on_finish)
        btn_box.append(finish_btn)
        box.append(btn_box)
        return box

    def _page_finish(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        box.set_margin_top(48); box.set_margin_bottom(48)
        box.set_margin_start(48); box.set_margin_end(48)
        box.set_valign(Gtk.Align.CENTER)

        self.finish_label = Gtk.Label()
        self.finish_label.set_markup("<span size='large'>Applying configuration...</span>")
        box.append(self.finish_label)

        self.finish_spinner = Gtk.Spinner()
        box.append(self.finish_spinner)

        self.finish_close_btn = Gtk.Button(label="Fechar")
        self.finish_close_btn.add_css_class("suggested-action")
        self.finish_close_btn.add_css_class("pill")
        self.finish_close_btn.set_halign(Gtk.Align.CENTER)
        self.finish_close_btn.set_visible(False)
        self.finish_close_btn.connect("clicked", lambda _: self.close())
        box.append(self.finish_close_btn)
        return box

    # ---------- Helpers visuais ----------
    def _title(self, text, size="x-large"):
        lbl = Gtk.Label()
        lbl.set_markup(f"<span size='{size}' weight='bold'>{text}</span>")
        return lbl

    def _body(self, text):
        lbl = Gtk.Label()
        lbl.set_wrap(True)
        lbl.set_markup(text)
        return lbl

    # ---------- Ações ----------
    def _on_oauth_start(self, btn):
        log.info("OAuth start clicked")
        if not _HAS_GOOGLE:
            self.oauth_status.set_markup(
                "<span color='#e01b24'>Error: Google Python packages not installed.\n\n"
                "Install with:\n"
                "<tt>sudo dnf install python3-google-auth python3-google-auth-oauthlib python3-google-api-client</tt></span>"
            )
            return

        if subprocess.run(["which", "rclone"], capture_output=True).returncode != 0:
            self.oauth_status.set_markup(
                "<span color='#e01b24'>Error: rclone is not installed.\n\n"
                "Install with:\n<tt>sudo dnf install rclone</tt></span>"
            )
            return

        self.oauth_btn.set_sensitive(False)
        self.oauth_cancel_btn.set_sensitive(True)
        self.oauth_status.set_markup("<span color='#3584e4'>Opening browser... please wait</span>")
        self.oauth_spinner.set_visible(True)
        self.oauth_spinner.start()

        self._cancel_oauth = False
        self._oauth_thread = threading.Thread(target=self._do_oauth)
        self._oauth_thread.daemon = True
        self._oauth_thread.start()

    def _on_oauth_cancel(self, btn):
        log.info("OAuth cancelled by user")
        self._cancel_oauth = True
        self.oauth_btn.set_sensitive(True)
        self.oauth_cancel_btn.set_sensitive(False)
        self.oauth_spinner.stop()
        self.oauth_status.set_text("Cancelado.")

    def _do_oauth(self):
        try:
            log.info("Starting OAuth flow with run_local_server")
            flow = InstalledAppFlow.from_client_config(
                {
                    "installed": {
                        "client_id": RCLONE_CLIENT_ID,
                        "client_secret": RCLONE_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
                    }
                },
                scopes=SCOPES
            )

            # run_local_server abre o navegador automaticamente e captura o callback
            # Isso bloqueia até o usuário autorizar ou dar timeout (120s default)
            creds = flow.run_local_server(port=0, prompt='consent', access_type='offline')
            log.info("OAuth completed successfully")

            if self._cancel_oauth:
                GLib.idle_add(self._oauth_error, "Cancelled by user")
                return

            self.creds = creds
            self._save_rclone_config(creds)
            log.info("Rclone config saved")

            # Listar drives compartilhados via API
            log.info("Fetching shared drives from Google API")
            service = build('drive', 'v3', credentials=creds, static_discovery=False)
            results = service.drives().list(pageSize=100).execute()
            self.drives = results.get('drives', [])
            log.info("Found %d shared drives", len(self.drives))

            # Sempre incluir Meu Drive
            self.drives.insert(0, {"id": "", "name": "Meu Drive (Pessoal)"})

            GLib.idle_add(self._show_drives_page)

        except Exception as e:
            log.exception("OAuth failed")
            GLib.idle_add(self._oauth_error, str(e))

    def _save_rclone_config(self, creds):
        os.makedirs(os.path.dirname(RCLONE_CONFIG), exist_ok=True)
        existing = ""
        if os.path.exists(RCLONE_CONFIG):
            with open(RCLONE_CONFIG) as f:
                existing = f.read()

        # Remover seção existente mountdesk-remote
        if "[mountdesk-remote]" in existing:
            lines = existing.split("\n")
            new_lines = []
            in_section = False
            for line in lines:
                if line.strip() == "[mountdesk-remote]":
                    in_section = True
                    new_lines.append(line)
                    continue
                if in_section and line.startswith("["):
                    in_section = False
                if not in_section:
                    new_lines.append(line)
            existing = "\n".join(new_lines)

        # rclone exige formato ISO 8601 completo com timezone offset
        if creds.expiry:
            expiry_str = creds.expiry.strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")
        else:
            expiry_str = ""

        token_json = json.dumps({
            "access_token": creds.token,
            "token_type": "Bearer",
            "refresh_token": creds.refresh_token,
            "expiry": expiry_str
        })

        section = f"""
[mountdesk-remote]
type = drive
client_id = {RCLONE_CLIENT_ID}
client_secret = {RCLONE_CLIENT_SECRET}
scope = drive
token = {token_json}
team_drive =
"""
        with open(RCLONE_CONFIG, "w") as f:
            f.write(existing.rstrip() + "\n" + section)
        os.chmod(RCLONE_CONFIG, 0o600)
        log.info("Saved rclone config to %s", RCLONE_CONFIG)

    def _show_drives_page(self):
        self.oauth_spinner.stop()
        self.oauth_btn.set_sensitive(True)
        self.oauth_cancel_btn.set_sensitive(False)
        self.stack.set_visible_child_name("drives")
        self._populate_drives()

    def _oauth_error(self, msg):
        log.error("OAuth error shown to user: %s", msg)
        self.oauth_spinner.stop()
        self.oauth_btn.set_sensitive(True)
        self.oauth_cancel_btn.set_sensitive(False)
        self.oauth_status.set_markup(f"<span color='#e01b24'>Erro: {msg}</span>")

    def _populate_drives(self):
        # Limpar lista
        while True:
            row = self.drives_box.get_first_child()
            if row is None:
                break
            self.drives_box.remove(row)
        self.drive_check_rows = []

        if not self.drives:
            self.drives_label.set_markup("<span color='#e01b24'>No drives found.</span>")
            return

        self.drives_label.set_text(f"{len(self.drives)} drive(s) found. Select which to mount:")

        for drive in self.drives:
            row = Adw.ActionRow()
            name = drive.get("name", "Sem nome")
            drive_id = drive.get("id", "")
            row.set_title(name)
            if drive_id:
                row.set_subtitle(f"ID: {drive_id[:24]}...")

            check = Gtk.CheckButton()
            check.set_active(True)
            row.add_prefix(check)

            self.drives_box.append(row)
            self.drive_check_rows.append((drive, check))

    def _on_drives_next(self, btn):
        self.selected_drives = []
        for drive, check in self.drive_check_rows:
            if check.get_active():
                self.selected_drives.append(drive)

        if not self.selected_drives:
            dialog = Adw.MessageDialog.new(self, "No drive selected",
                "Select at least one drive to continue.")
            dialog.add_response("ok", "OK")
            dialog.present()
            return

        self._build_mounts_from_selection()
        self.stack.set_visible_child_name("mounts")

    def _build_mounts_from_selection(self):
        # Limpar
        while True:
            row = self.mounts_box.get_first_child()
            if row is None:
                break
            self.mounts_box.remove(row)

        self.mount_rows = []
        for drive in self.selected_drives:
            name = drive.get("name", "drive")
            drive_id = drive.get("id", "")
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', name.replace(' ', '_'))

            row = Adw.ActionRow()
            row.set_title(name)

            entry = Gtk.Entry()
            entry.set_text(os.path.join(MOUNT_BASE, safe_name))
            entry.set_width_chars(35)
            row.add_suffix(entry)
            row.drive_id = drive_id

            self.mounts_box.append(row)
            self.mount_rows.append((drive, entry))

    def _on_finish(self, btn):
        log.info("Applying configuration")
        drives_config = []

        for drive, entry in self.mount_rows:
            name = drive.get("name", "drive")
            drive_id = drive.get("id", "")
            mountpoint = entry.get_text()
            safe_name = name.replace(" ", "_").replace("/", "_")

            remote_name = f"mountdesk-{safe_name.lower()}"
            self._add_rclone_remote(remote_name, drive_id)

            drives_config.append({
                "name": name,
                "remote": remote_name,
                "mountpoint": mountpoint
            })
            log.info("Drive '%s' -> remote '%s' -> '%s'", name, remote_name, mountpoint)

        config = {
            "drives": drives_config,
            "settings": {
                "tray_refresh_interval": 5,
                "icons": {
                    "sheets": "google-sheets",
                    "docs": "google-docs",
                    "slides": "google-slides"
                }
            }
        }

        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        log.info("Saved config to %s", CONFIG_PATH)

        self.stack.set_visible_child_name("finish")
        self._run_setup()

    def _add_rclone_remote(self, remote_name, team_drive_id):
        existing = ""
        if os.path.exists(RCLONE_CONFIG):
            with open(RCLONE_CONFIG) as f:
                existing = f.read()

        # Remover seção existente
        if f"[{remote_name}]" in existing:
            lines = existing.split("\n")
            new_lines = []
            in_section = False
            for line in lines:
                if line.strip() == f"[{remote_name}]":
                    in_section = True
                    continue
                if in_section and line.startswith("["):
                    in_section = False
                if not in_section:
                    new_lines.append(line)
            existing = "\n".join(new_lines)

        # Extrair token do remote base
        token = ""
        if "[mountdesk-remote]" in existing:
            lines = existing.split("\n")
            in_section = False
            for line in lines:
                if line.strip() == "[mountdesk-remote]":
                    in_section = True
                    continue
                if in_section and line.startswith("["):
                    break
                if in_section and line.startswith("token ="):
                    token = line.split("=", 1)[1].strip()
                    break

        section = f"""
[{remote_name}]
type = drive
client_id = {RCLONE_CLIENT_ID}
client_secret = {RCLONE_CLIENT_SECRET}
scope = drive
token = {token}
team_drive = {team_drive_id}
"""
        with open(RCLONE_CONFIG, "w") as f:
            f.write(existing.rstrip() + "\n" + section)
        os.chmod(RCLONE_CONFIG, 0o600)
        log.info("Added rclone remote '%s' with team_drive='%s'", remote_name, team_drive_id)

    def _run_setup(self):
        self.finish_label.set_markup("<span size='large'>Configuring services...</span>")
        self.finish_spinner.start()
        self.finish_close_btn.set_visible(False)

        def do_setup():
            try:
                result = subprocess.run(
                    ["/usr/bin/bash", os.path.expanduser("~/.local/lib/mountdesk/setup.sh")],
                    capture_output=True, text=True, timeout=180
                )
                ok = result.returncode == 0
                out = result.stdout + result.stderr
                log.info("Setup output:\n%s", out)
                GLib.idle_add(self._setup_done, ok, out)
            except Exception as e:
                log.exception("Setup failed")
                GLib.idle_add(self._setup_done, False, str(e))

        t = threading.Thread(target=do_setup)
        t.daemon = True
        t.start()

    def _setup_done(self, ok, output):
        self.finish_spinner.stop()
        self.finish_close_btn.set_visible(True)
        if ok:
            self.finish_label.set_markup(
                "<span size='x-large' weight='bold' color='#26a269'>✓ Pronto!</span>\n\n"
                "Your drives are mounted and accessible.\n"
                "Check the system tray icon and file manager."
            )
            log.info("Setup completed successfully")
        else:
            self.finish_label.set_markup(
                f"<span color='#e01b24'>Configuration error:</span>\n\n"
                f"<tt>{output[-800:]}</tt>"
            )
            log.error("Setup failed: %s", output)


class WizardApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.mountdesk.wizard")
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        win = WizardWindow(app)
        win.present()


def main():
    app = WizardApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
