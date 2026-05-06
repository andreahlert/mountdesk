Name:           mountdesk
Version:        1.0.3
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
Requires:       python3-google-auth
Requires:       python3-google-auth-oauthlib
Requires:       python3-google-api-client
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
install -Dm755 src/bin/mountdesk-open-file       %{buildroot}%{_bindir}/mountdesk-open-file

# Tray app and helpers
install -Dm755 src/lib/mountdesk-tray.py         %{buildroot}%{_libdir}/mountdesk/mountdesk-tray.py
install -Dm755 src/lib/setup.sh                  %{buildroot}%{_libdir}/mountdesk/setup.sh
install -Dm755 src/lib/fix-keyring.sh            %{buildroot}%{_libdir}/mountdesk/fix-keyring.sh
install -Dm755 src/lib/mountdesk-wizard.py    %{buildroot}%{_libdir}/mountdesk/mountdesk-wizard.py
install -Dm755 src/lib/mountdesk-app.py       %{buildroot}%{_libdir}/mountdesk/mountdesk-app.py


# Default config
install -Dm644 src/config/config.yaml            %{buildroot}%{_sysconfdir}/mountdesk/config.yaml.example

# Nemo extension
install -Dm644 src/nemo/mountdesk-nemo.py        %{buildroot}%{_datadir}/nemo-python/extensions/mountdesk-nemo.py

# Desktop entries
install -Dm644 src/desktop/mountdesk.desktop     %{buildroot}%{_datadir}/applications/mountdesk.desktop
install -Dm644 src/desktop/mountdesk-wizard.desktop %{buildroot}%{_datadir}/applications/mountdesk-wizard.desktop
install -Dm644 src/desktop/mountdesk-handler.desktop %{buildroot}%{_datadir}/applications/mountdesk-handler.desktop
sed -i "s|/usr/lib/mountdesk|%{_libdir}/mountdesk|g" %{buildroot}%{_datadir}/applications/mountdesk.desktop
sed -i "s|/usr/lib/mountdesk|%{_libdir}/mountdesk|g" %{buildroot}%{_datadir}/applications/mountdesk-wizard.desktop

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
install -Dm644 src/systemd/mountdesk-tray.service  %{buildroot}/usr/lib/systemd/user/mountdesk-tray.service
sed -i "s|/usr/lib/mountdesk|%{_libdir}/mountdesk|g" %{buildroot}/usr/lib/systemd/user/mountdesk-tray.service

# AppData / Metainfo
install -Dm644 src/metainfo/com.mountdesk.drive.metainfo.xml %{buildroot}%{_metainfodir}/com.mountdesk.drive.metainfo.xml

# MIME override for zero-size FUSE files
install -Dm644 src/mime/override-rclone-empty.xml %{buildroot}%{_datadir}/mime/packages/mountdesk.xml

%files
%license LICENSE
%doc README.md
%config(noreplace) %{_sysconfdir}/mountdesk/config.yaml.example
%{_bindir}/mountdesk-open-link
%{_bindir}/mountdesk-fix-icons
%{_bindir}/mountdesk-open-file
%{_libdir}/mountdesk/
%{_datadir}/nemo-python/extensions/mountdesk-nemo.py
%{_datadir}/applications/mountdesk.desktop
%{_datadir}/applications/mountdesk-wizard.desktop
%{_datadir}/applications/mountdesk-handler.desktop
%{_datadir}/icons/hicolor/*/apps/google-sheets.png
%{_datadir}/icons/hicolor/*/apps/google-docs.png
%{_datadir}/icons/hicolor/*/apps/google-slides.png
%{_datadir}/icons/hicolor/256x256/apps/mountdesk.png
%{_datadir}/icons/hicolor/scalable/apps/mountdesk.svg
/usr/lib/systemd/user/mountdesk-tray.service
%{_metainfodir}/com.mountdesk.drive.metainfo.xml
%{_datadir}/mime/packages/mountdesk.xml

%post
update-desktop-database -q %{_datadir}/applications &> /dev/null || :
update-mime-database -n %{_datadir}/mime &> /dev/null || :

%postun
update-desktop-database -q %{_datadir}/applications &> /dev/null || :
update-mime-database -n %{_datadir}/mime &> /dev/null || :

%changelog
* Wed May 06 2026 André Ahlert Junior <andreahlert@gmail.com> - 1.0.3-1
- AppStream metainfo: fix homepage URL, add categories, keywords, bugtracker, vcs-browser
- Replace deprecated developer_name with developer block (required for GNOME Software listing)
- Add 1.0.1, 1.0.2, 1.0.3 release entries

* Wed May 06 2026 André Ahlert Junior <andreahlert@gmail.com> - 1.0.2-1
- Fix collisions when multiple shared drives share a name: dedup remote/mountpoint via drive_id suffix
- Slugify drive names (strip accents, parentheses, special chars) for safe systemd unit and rclone remote names
- Use drive["remote"] as canonical service name across tray/app/setup, removing fragile name-regex paths
- Sweep stale mountdesk-*.service units on setup so renamed/removed drives don't linger

* Wed May 06 2026 André Ahlert Junior <andreahlert@gmail.com> - 1.0.1-1
- Fix wizard NameError: missing 're' import broke drive selection
- Fix tray service path (was hardcoded to ~/.local/lib, now /usr/lib)
- Fix nemo extension and setup.sh helper paths
- Add mountdesk-handler.desktop registering MIME types for app-window open
- Persist OAuth account email and inject ?authuser= to fix multi-account redirect
- Simplify tray menu to drives + Configure + Quit
- Run update-desktop-database / update-mime-database on install

* Mon May 04 2026 André Ahlert Junior <andreahlert@gmail.com> - 1.0.0-1
- Generic cloud drive desktop integration
- YAML-configurable drives
- Automatic systemd service generation
