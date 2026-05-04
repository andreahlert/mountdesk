import gi
#!/usr/bin/env python3
"""
MountDesk - Nemo extension for Google Drive mounted folders.
Reads drive configuration from ~/.config/mountdesk/config.yaml
Provides colored emblems and "Open in Google Drive" context menu.
"""

import os
import yaml
import urllib.parse
import subprocess

gi.require_version('Nemo', '3.0')
from gi.repository import Nemo, GObject, Gio

CONFIG_PATH = os.path.expanduser("~/.config/mountdesk/config.yaml")


def load_mount_paths():
    try:
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f) or {}
        paths = []
        for drive in config.get("drives", []):
            mp = os.path.expanduser(drive.get("mountpoint", ""))
            if mp:
                paths.append("file://" + mp)
        return paths
    except Exception:
        return []


def is_in_mount(file_info):
    uri = file_info.get_uri()
    return any(uri.startswith(mp) for mp in load_mount_paths())


class MountDeskExtension(GObject.GObject, Nemo.ColumnProvider, Nemo.InfoProvider):
    def update_file_info(self, file):
        if not is_in_mount(file):
            return
        name = file.get_name()
        if name.endswith(('.xlsx', '.csv', '.ods')):
            file.add_emblem('new')
        elif name.endswith(('.docx', '.odt', '.txt')):
            file.add_emblem('favorite')
        elif name.endswith(('.pptx', '.odp')):
            file.add_emblem('important')


class MountDeskMenuProvider(GObject.GObject, Nemo.MenuProvider):
    def _open_in_gdrive(self, menu, files):
        for f in files:
            path = urllib.parse.unquote(f.get_uri()[7:])
            subprocess.Popen([os.path.expanduser('~/bin/mountdesk-open-link'), path])

    def get_file_items(self, window, files):
        if not files or not is_in_mount(files[0]):
            return []
        item = Nemo.MenuItem(name='MountDesk::OpenInGDrive',
                             label='Abrir no Google Drive',
                             tip='Abrir arquivo no Google Drive')
        item.connect('activate', self._open_in_gdrive, files)
        return [item]

    def get_background_items(self, window, file):
        return []
