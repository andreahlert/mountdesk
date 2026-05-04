#!/usr/bin/env python3
"""
MountDesk Setup Wizard
GUI simples para configurar drives sem editar texto.
"""

import os
import sys
import subprocess
import yaml

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

CONFIG_DIR = os.path.expanduser("~/.config/mountdesk")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.yaml")
MOUNT_BASE = os.path.expanduser("~/GoogleDrive")


class WizardWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("MountDesk - Configuração")
        self.set_default_size(600, 500)

        self.stack = Adw.ViewStack()
        self.set_content(self.stack)

        self.stack.add_named(self._page_welcome(), "welcome")
        self.stack.add_named(self._page_rclone(), "rclone")
        self.stack.add_named(self._page_drives(), "drives")
        self.stack.add_named(self._page_finish(), "finish")

        self.stack.set_visible_child_name("welcome")

    def _page_welcome(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(40)
        box.set_margin_bottom(40)
        box.set_margin_start(40)
        box.set_margin_end(40)
        box.set_valign(Gtk.Align.CENTER)

        img = Gtk.Image.new_from_icon_name("drive-harddisk")
        img.set_pixel_size(80)
        box.append(img)

        box.append(self._title("MountDesk"))
        box.append(self._body("Configure seus Google Drives sem editar arquivos de texto."))
        box.append(self._body("Passos:\n1. Crie seus remotes no rclone\n2. Selecione quais montar\n3. Pronto!"))

        btn = Gtk.Button(label="Começar")
        btn.add_css_class("suggested-action")
        btn.add_css_class("pill")
        btn.set_halign(Gtk.Align.CENTER)
        btn.connect("clicked", lambda _: self.stack.set_visible_child_name("rclone"))
        box.append(btn)

        return box

    def _page_rclone(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(30)
        box.set_margin_bottom(30)
        box.set_margin_start(30)
        box.set_margin_end(30)

        box.append(self._title("Passo 1: Conectar ao Google"))
        box.append(self._body(
            "Vamos abrir o terminal para você configurar o acesso ao Google Drive.\n\n"
            "No terminal que abrir:\n"
            "• Digite <b>n</b> para novo remote\n"
            "• Dê um nome (ex: <b>gdrive</b>)\n"
            "• Escolha <b>drive</b> (Google Drive)\n"
            "• Siga o login no navegador\n"
            "• Cole o código no terminal\n"
            "• Digite <b>q</b> para sair\n\n"
            "Repita para cada conta/drive que quiser."
        ))

        btn_term = Gtk.Button(label="Abrir Terminal (rclone config)")
        btn_term.add_css_class("suggested-action")
        btn_term.set_halign(Gtk.Align.CENTER)
        btn_term.connect("clicked", self._open_rclone_config)
        box.append(btn_term)

        btn_refresh = Gtk.Button(label="Já configurei → Listar meus drives")
        btn_refresh.set_halign(Gtk.Align.CENTER)
        btn_refresh.connect("clicked", self._refresh_drives)
        box.append(btn_refresh)

        back = Gtk.Button(label="Voltar")
        back.set_halign(Gtk.Align.CENTER)
        back.connect("clicked", lambda _: self.stack.set_visible_child_name("welcome"))
        box.append(back)

        return box

    def _open_rclone_config(self, btn):
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c",
            "echo '=== RCLONE CONFIG ==='; rclone config; echo ''; echo 'Feche esta janela quando terminar.'; read"])

    def _refresh_drives(self, btn):
        self.stack.set_visible_child_name("drives")
        self._load_drives()

    def _page_drives(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.set_margin_start(20)
        box.set_margin_end(20)

        box.append(self._title("Passo 2: Selecionar Drives"))
        self.drives_label = self._body("Carregando...")
        box.append(self.drives_label)

        self.drives_box = Gtk.ListBox()
        self.drives_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.drives_box.add_css_class("boxed-list")
        box.append(self.drives_box)

        btn_apply = Gtk.Button(label="Aplicar e Montar")
        btn_apply.add_css_class("suggested-action")
        btn_apply.set_halign(Gtk.Align.CENTER)
        btn_apply.set_margin_top(16)
        btn_apply.connect("clicked", self._apply_config)
        box.append(btn_apply)

        return box

    def _load_drives(self):
        # Clear
        while True:
            row = self.drives_box.get_first_child()
            if row is None:
                break
            self.drives_box.remove(row)

        self.drive_checks = []

        try:
            result = subprocess.run(["rclone", "listremotes"], capture_output=True, text=True)
            remotes = [r.strip().rstrip(":") for r in result.stdout.strip().split("\n") if r.strip()]
        except Exception as e:
            self.drives_label.set_markup(f"<span color='#e01b24'>Erro: {e}</span>")
            return

        if not remotes:
            self.drives_label.set_markup(
                "<span color='#e01b24'>Nenhum remote encontrado.</span>\n"
                "Clique 'Voltar' e configure pelo terminal primeiro."
            )
            return

        self.drives_label.set_text(f"Encontrados {len(remotes)} remotes. Selecione quais montar:")

        for remote in remotes:
            row = Adw.ActionRow()
            row.set_title(remote)

            check = Gtk.CheckButton()
            check.set_active(True)
            row.add_prefix(check)

            entry = Gtk.Entry()
            entry.set_text(os.path.join(MOUNT_BASE, remote.replace(" ", "_")))
            entry.set_width_chars(25)
            row.add_suffix(entry)

            self.drives_box.append(row)
            self.drive_checks.append((remote, check, entry))

    def _apply_config(self, btn):
        drives = []
        for remote, check, entry in self.drive_checks:
            if check.get_active():
                drives.append({
                    "name": remote,
                    "remote": remote,
                    "mountpoint": entry.get_text()
                })

        if not drives:
            dialog = Adw.MessageDialog.new(self, "Nenhum drive selecionado",
                "Selecione pelo menos um drive para continuar.")
            dialog.add_response("ok", "OK")
            dialog.present()
            return

        config = {
            "drives": drives,
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

        self.stack.set_visible_child_name("finish")
        self._run_setup()

    def _run_setup(self):
        self.finish_label.set_text("Aplicando configuração...")
        self.finish_spinner.start()

        def do_setup():
            try:
                result = subprocess.run(
                    ["/usr/lib/mountdesk/setup.sh"],
                    capture_output=True, text=True, timeout=180
                )
                ok = result.returncode == 0
                out = result.stdout + result.stderr
                GLib.idle_add(self._setup_done, ok, out)
            except Exception as e:
                GLib.idle_add(self._setup_done, False, str(e))

        import threading
        t = threading.Thread(target=do_setup)
        t.daemon = True
        t.start()

    def _setup_done(self, ok, output):
        self.finish_spinner.stop()
        if ok:
            self.finish_label.set_markup(
                "<span size='x-large' weight='bold' color='#26a269'>✓ Pronto!</span>\n\n"
                "Seus drives estão montados.\n"
                "Verifique o ícone na bandeja do sistema."
            )
        else:
            self.finish_label.set_markup(
                f"<span color='#e01b24'>Erro:</span>\n<tt>{output[-800:]}</tt>"
            )

    def _page_finish(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(40)
        box.set_margin_bottom(40)
        box.set_margin_start(40)
        box.set_margin_end(40)
        box.set_valign(Gtk.Align.CENTER)

        self.finish_label = Gtk.Label()
        self.finish_label.set_markup("<span size='large'>Aplicando...</span>")
        box.append(self.finish_label)

        self.finish_spinner = Gtk.Spinner()
        box.append(self.finish_spinner)

        btn = Gtk.Button(label="Fechar")
        btn.add_css_class("suggested-action")
        btn.set_halign(Gtk.Align.CENTER)
        btn.connect("clicked", lambda _: self.close())
        box.append(btn)

        return box

    def _title(self, text):
        lbl = Gtk.Label()
        lbl.set_markup(f"<span size='x-large' weight='bold'>{text}</span>")
        return lbl

    def _body(self, text):
        lbl = Gtk.Label()
        lbl.set_wrap(True)
        lbl.set_markup(text)
        return lbl


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
