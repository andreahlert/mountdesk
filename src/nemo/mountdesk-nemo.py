#!/usr/bin/env python3
"""
MountDesk Nemo Extension
Context menu: "Open in Google Drive"
(No emblemas - ícones limpos e sóbrios)
"""

import os
import subprocess
import urllib.parse
import yaml

import gi
gi.require_version('Nemo', '3.0')
from gi.repository import Nemo, GObject

CONFIG_PATH = os.path.expanduser("~/.config/mountdesk/config.yaml")


def load_mount_paths():
    try:
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f) or {}
        return [os.path.expanduser(d['mountpoint']) for d in config.get('drives', [])]
    except Exception:
        return []


def is_in_mount(file):
    uri = file.get_uri()
    for mp in load_mount_paths():
        if uri.startswith('file://' + mp):
            return True
    return False


class MountDeskExtension(GObject.GObject, Nemo.InfoProvider):
    """Extension without emblems - icons remain sober."""
    def update_file_info(self, file):
        # Emblemas removidos por pedido do usuário
        pass


class MountDeskMenuProvider(GObject.GObject, Nemo.MenuProvider):
    def _open_in_gdrive(self, menu, files):
        for f in files:
            path = urllib.parse.unquote(f.get_uri()[7:])
            subprocess.Popen([os.path.expanduser('~/bin/mountdesk-open-link'), path])

    def get_file_items(self, window, files):
        if not files or not is_in_mount(files[0]):
            return []

        item = Nemo.MenuItem(
            name="MountDesk::OpenInGDrive",
            label="Abrir no Google Drive",
            tip="Open this file in the Google Drive browser"
        )
        item.connect("activate", self._open_in_gdrive, files)
        return [item]
