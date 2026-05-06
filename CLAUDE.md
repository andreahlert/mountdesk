# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

MountDesk: Fedora/GNOME desktop integration for cloud storage via `rclone` FUSE mounts. Python 3 + GTK4/Adw (main app, wizard) + GTK3/AppIndicator3 (tray) + Nemo extension. Distributed as a noarch RPM (Copr `andreahlert/mountdesk`).

No build step for code, all Python scripts. "Build" means producing the RPM.

## Common commands

```bash
make rpm                                  # build RPM into ~/rpmbuild/RPMS/noarch/
make install                              # install built RPM via dnf
make clean                                # wipe rpmbuild artifacts for this package
bash make_srpm.sh <outdir>                # SRPM build path (used by Copr via .copr/Makefile)
rpmlint ~/rpmbuild/RPMS/noarch/*.rpm      # spec lint
```

Run components without packaging (point them at the in-repo files):

```bash
python3 src/lib/mountdesk-app.py
python3 src/lib/mountdesk-wizard.py
python3 src/lib/mountdesk-tray.py
bash    src/lib/setup.sh                  # generates per-drive systemd units, starts tray
```

Wizard log: `/tmp/mountdesk-wizard.log` (DEBUG level).

There is no test suite, no linter config, no CI step beyond `rpmbuild` + `rpmlint` (`.github/workflows/build.yml`). Releases on tag `v*` upload artifacts via `softprops/action-gh-release`.

## Architecture

User-level only: nothing runs as root. State lives in `~/.config/mountdesk/`, `~/.config/rclone/`, `~/.config/systemd/user/`. Mounts default under `~/GoogleDrive/`.

Single source of truth = `~/.config/mountdesk/config.yaml` with shape:

```yaml
drives:
  - name: "<display name>"
    remote: "<rclone remote>"        # e.g. gdrive, gdrive-work
    mountpoint: "~/GoogleDrive/Foo"
settings:
  tray_refresh_interval: 5
```

Components and how they connect:

- **Wizard** (`src/lib/mountdesk-wizard.py`, GTK4/Adw) does Google OAuth using rclone's public client ID, writes `~/.config/rclone/rclone.conf`, picks shared drives, writes `config.yaml`, then invokes `setup.sh`.
- **setup.sh** (`src/lib/setup.sh`) is the apply step: reads `config.yaml`, generates one `mountdesk-<slug>.service` per drive into `~/.config/systemd/user/` with `rclone mount --vfs-cache-mode full ...`, `daemon-reload`, enable+start, then ensures `mountdesk-tray.service` is running. The same unit template also exists in `mountdesk-tray.py::ensure_service` so the tray can self-heal a missing unit; if you change rclone flags, change BOTH.
- **Service naming** is derived from `name`: lowercase, spaces→`-`, then `[^a-z0-9-]` stripped, prefixed `mountdesk-`. Same regex appears in `setup.sh`, `mountdesk-tray.py`, `mountdesk-app.py` (`svc_name`). Keep them in sync.
- **App window** (`src/lib/mountdesk-app.py`, GTK4/Adw) is a status/control UI: lists drives from `config.yaml`, queries `systemctl --user is-active mountdesk-<slug>`, exposes start/stop/open buttons. Configure button shells out to `mountdesk-wizard` (system path).
- **Tray** (`src/lib/mountdesk-tray.py`, GTK3 + AppIndicator3, runs as `mountdesk-tray.service`). Lives in GTK3 because libappindicator-gtk3 has no working GTK4 equivalent. Don't unify the toolkits.
- **Nemo extension** (`src/nemo/mountdesk-nemo.py`, installed to `/usr/share/nemo-python/extensions/`) adds the "Open in Google Drive" right-click and emblem hints inside mountpoints.
- **CLI helpers** in `src/bin/`:
  - `mountdesk-open-file`: double-click handler. If file is inside a configured mountpoint AND extension is in `EXT_TO_GTYPE` (xlsx/docx/pptx/ods/odt/odp/csv), uses `rclone lsjson` to fetch the Drive file ID/MimeType and opens `docs.google.com/{document|spreadsheets|presentation}/d/<id>/edit` in `chrome --app=` (falls back to xdg-open). Otherwise delegates to xdg-open.
  - `mountdesk-open-link`: opens drive URLs in app-window mode.
  - `mountdesk-fix-icons`: re-applies Google Docs/Sheets/Slides icons after install.
- **MIME override** (`src/mime/override-rclone-empty.xml`): rclone exposes Google-native files as zero-byte; the override forces correct MIME so Nemo can show the right icon and `mountdesk-open-file` is invoked.

## Packaging notes

- Spec is `rpm/mountdesk.spec`, version bumped there (also referenced by `Makefile` and `make_srpm.sh`). Three places — keep aligned.
- Library files install to `%{_libdir}/mountdesk/` (multi-arch aware: `/usr/lib64` on x86_64, `/usr/lib` on noarch consumers). Desktop entries are `sed`-rewritten at install time to substitute the literal `/usr/lib/mountdesk` placeholder with `%{_libdir}/mountdesk`. If you add a new desktop entry that references the lib path, mirror that `sed` line in the spec.
- The wizard `.desktop` is hidden from the app grid (`NoDisplay=true`), launched from the app window's Configure button.
- Tarball must contain `src rpm LICENSE README.md assets` rooted at `mountdesk-<version>/` for `%autosetup` to work — see `Makefile`, `make_srpm.sh`, and the GH Actions workflow (all three build the same shape).
- Copr uses `make_srpm` method via `.copr/Makefile` → `make_srpm.sh`.

## Conventions specific to this repo

- Status checks always go through `systemctl --user is-active <unit>`. Don't probe FUSE mounts directly.
- New rclone mount flags must be added in BOTH `setup.sh` and `mountdesk-tray.py::ensure_service`.
- Don't introduce a venv or pip dependencies — runtime deps come from Fedora RPMs (`python3-pyyaml`, `python3-google-auth*`, `python3-google-api-client`, `python3-gobject`, `gtk3`, `libappindicator-gtk3`). Add new deps to `Requires:` in the spec.
- OAuth uses rclone's public client ID/secret (`RCLONE_CLIENT_ID`/`RCLONE_CLIENT_SECRET` constants in the wizard) — these are public on purpose, not credentials to rotate.
