Name:           mountdesk
Version:        1.0.0
Release:        1%{?dist}
Summary:        MountDesk - Generic cloud drive desktop integration via rclone FUSE
License:        MIT
URL:            https://github.com/mountdesk/mountdesk
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

Requires:       rclone
Requires:       nemo-python
Requires:       python3-gobject
Requires:       python3-gobject-base
Requires:       python3-pyyaml
Requires:       gtk3
Requires:       libappindicator-gtk3
Requires:       python3
Requires:       jq
Recommends:     google-chrome-stable

%description
MountDesk integrates any cloud storage (Google Drive, OneDrive, Dropbox,
etc.) into the Fedora/GNOME desktop via rclone FUSE mounts.

Features:
- Configure any number of drives via YAML config
- Automatic rclone FUSE mounts on login
- System tray with per-drive status and controls
- Nemo file manager extension with colored emblems
- "Open in Google Drive" right-click context menu
- Correct icons for Google Docs/Sheets/Slides exports

%prep
%autosetup

%build
# Nothing to build (Python scripts)

%install
# Scripts
install -Dm755 src/bin/mountdesk-open-link       %{buildroot}%{_bindir}/mountdesk-open-link
install -Dm755 src/bin/mountdesk-fix-icons       %{buildroot}%{_bindir}/mountdesk-fix-icons

# Tray app and helpers
install -Dm755 src/lib/mountdesk-tray.py         %{buildroot}%{_libdir}/mountdesk/mountdesk-tray.py
install -Dm755 src/lib/setup.sh                  %{buildroot}%{_libdir}/mountdesk/setup.sh
install -Dm755 src/lib/fix-keyring.sh            %{buildroot}%{_libdir}/mountdesk/fix-keyring.sh


# Default config
install -Dm644 src/config/config.yaml            %{buildroot}%{_sysconfdir}/mountdesk/config.yaml.example

# Nemo extension
install -Dm644 src/nemo/mountdesk-nemo.py        %{buildroot}%{_datadir}/nemo-python/extensions/mountdesk-nemo.py

# Desktop entry
install -Dm644 src/desktop/mountdesk.desktop     %{buildroot}%{_datadir}/applications/mountdesk.desktop

# Icons
install -Dm644 src/icons/48x48/google-sheets.png   %{buildroot}%{_datadir}/icons/hicolor/48x48/apps/google-sheets.png
install -Dm644 src/icons/48x48/google-docs.png     %{buildroot}%{_datadir}/icons/hicolor/48x48/apps/google-docs.png
install -Dm644 src/icons/48x48/google-slides.png   %{buildroot}%{_datadir}/icons/hicolor/48x48/apps/google-slides.png
install -Dm644 src/icons/128x128/google-sheets.png %{buildroot}%{_datadir}/icons/hicolor/128x128/apps/google-sheets.png
install -Dm644 src/icons/128x128/google-docs.png   %{buildroot}%{_datadir}/icons/hicolor/128x128/apps/google-docs.png
install -Dm644 src/icons/128x128/google-slides.png %{buildroot}%{_datadir}/icons/hicolor/128x128/apps/google-slides.png
install -Dm644 src/icons/256x256/mountdesk.png     %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/mountdesk.png
install -Dm644 src/icons/scalable/mountdesk.svg    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/mountdesk.svg

# Systemd user service (tray only - mounts are generated dynamically)
install -Dm644 src/systemd/mountdesk-tray.service  %{buildroot}%{_userunitdir}/mountdesk-tray.service

# AppData / Metainfo
install -Dm644 src/metainfo/com.mountdesk.drive.metainfo.xml %{buildroot}%{_metainfodir}/com.mountdesk.drive.metainfo.xml

# MIME override for zero-size FUSE files
install -Dm644 src/mime/override-rclone-empty.xml %{buildroot}%{_datadir}/mime/packages/mountdesk.xml

%post
%systemd_user_post mountdesk-tray.service

%preun
%systemd_user_preun mountdesk-tray.service

%files
%license LICENSE
%doc README.md
%config(noreplace) %{_sysconfdir}/mountdesk/config.yaml.example
%{_bindir}/mountdesk-open-link
%{_bindir}/mountdesk-fix-icons
%{_libdir}/mountdesk/
%{_datadir}/nemo-python/extensions/mountdesk-nemo.py
%{_datadir}/applications/mountdesk.desktop
%{_datadir}/icons/hicolor/*/apps/google-sheets.png
%{_datadir}/icons/hicolor/*/apps/google-docs.png
%{_datadir}/icons/hicolor/*/apps/google-slides.png
%{_datadir}/icons/hicolor/256x256/apps/mountdesk.png
%{_datadir}/icons/hicolor/scalable/apps/mountdesk.svg
%{_userunitdir}/mountdesk-tray.service
%{_metainfodir}/com.mountdesk.drive.metainfo.xml
%{_datadir}/mime/packages/mountdesk.xml

%changelog
* Sun May 04 2026 André Ahlert Junior <andreahlert@gmail.com> - 1.0.0-1
- Generic cloud drive desktop integration
- YAML-configurable drives
- Automatic systemd service generation
