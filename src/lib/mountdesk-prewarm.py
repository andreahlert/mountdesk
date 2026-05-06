#!/usr/bin/env python3
"""
MountDesk Pre-warm — walks each mountpoint to populate Nemo/GVfs metadata
and rclone dir-cache so first navigation feels instant.

Writes /tmp/mountdesk-prewarm.status (read by tray) and /tmp/mountdesk-prewarm.done.
"""

import os
import sys
import time
import threading
import subprocess
import yaml

CONFIG_PATH = os.path.expanduser("~/.config/mountdesk/config.yaml")
STATUS_FILE = "/tmp/mountdesk-prewarm.status"
DONE_FILE = "/tmp/mountdesk-prewarm.done"


def is_mounted(path):
    return subprocess.run(
        ["mountpoint", "-q", path], check=False
    ).returncode == 0


_status_lock = threading.Lock()


def write_status(text):
    with _status_lock:
        try:
            with open(STATUS_FILE, "w") as f:
                f.write(text)
        except Exception:
            pass


def cleanup():
    try:
        os.remove(STATUS_FILE)
    except FileNotFoundError:
        pass
    except Exception:
        pass


def warm_drive(mp):
    # Stat each top-level entry so Nemo's first cold-open returns from
    # kernel inode cache instead of round-tripping FUSE -> rclone.
    try:
        for entry in os.scandir(mp):
            try:
                entry.stat()
            except Exception:
                pass
    except Exception as e:
        print(f"prewarm: error scanning {mp}: {e}", file=sys.stderr)


def main():
    try:
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"prewarm: cannot read config: {e}", file=sys.stderr)
        return 1

    drives = config.get("drives", [])
    if not drives:
        return 0

    deadline = time.time() + 30
    while time.time() < deadline:
        if any(is_mounted(os.path.expanduser(d["mountpoint"])) for d in drives):
            break
        time.sleep(1)

    try:
        os.remove(DONE_FILE)
    except FileNotFoundError:
        pass

    n = len(drives)
    completed = [0]
    completed_lock = threading.Lock()

    def worker(idx, drive):
        name = drive.get("name", "drive")
        mp = os.path.expanduser(drive["mountpoint"])
        if is_mounted(mp):
            warm_drive(mp)
        with completed_lock:
            completed[0] += 1
            write_status(f"{completed[0]}/{n} {name}")

    threads = []
    for i, drive in enumerate(drives, 1):
        t = threading.Thread(target=worker, args=(i, drive), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    cleanup()
    try:
        with open(DONE_FILE, "w") as f:
            f.write(str(int(time.time())))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
