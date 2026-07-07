#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = ["rich"]
# ///
"""
Set up automatic chezmoi re-add via systemd path units.

Watches all chezmoi-managed files and runs 'chezmoi re-add' on change.
This keeps the repo in sync when you edit dotfiles directly.

Usage:
  uv run scripts/setup_watch.py        # install + enable + start
  uv run scripts/setup_watch.py status  # check status
  uv run scripts/setup_watch.py stop   # stop watching
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.ui import info, warn, ok, run

UNIT_NAME = "chezmoi-watch"
SERVICE_DIR = Path.home() / ".config/systemd/user"


def get_managed_files() -> list[str]:
    result = subprocess.run(
        ["chezmoi", "managed", "--include=files", "--path-style=absolute"],
        capture_output=True, text=True, check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def generate_units(files: list[str]) -> tuple[str, str]:
    escaped = [f.replace("%", "%%") for f in files]

    path_unit = f"""\
[Unit]
Description=Watch chezmoi-managed dotfiles

[Path]
{chr(10).join(f"PathModified={f}" for f in escaped)}

[Install]
WantedBy=default.target
"""

    service_unit = f"""\
[Unit]
Description=Re-add changed dotfiles to chezmoi
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/chezmoi re-add
ExecStartPost=/bin/sh -c 'cd {Path.cwd()} && git diff --quiet 2>/dev/null || echo "repo has uncommitted changes"'

[Install]
WantedBy=default.target
"""
    return path_unit, service_unit


def install_units(path_unit: str, service_unit: str) -> None:
    SERVICE_DIR.mkdir(parents=True, exist_ok=True)
    path_file = SERVICE_DIR / f"{UNIT_NAME}.path"
    service_file = SERVICE_DIR / f"{UNIT_NAME}.service"

    path_file.write_text(path_unit)
    service_file.write_text(service_unit)
    info(f"wrote {path_file}")
    info(f"wrote {service_file}")


def enable_and_start() -> None:
    for unit in [f"{UNIT_NAME}.path", f"{UNIT_NAME}.service"]:
        run(["systemctl", "--user", "daemon-reload"])
    run(["systemctl", "--user", "enable", "--now", f"{UNIT_NAME}.path"])
    info(f"enabled and started {UNIT_NAME}.path")


def status() -> None:
    result = subprocess.run(
        ["systemctl", "--user", "status", f"{UNIT_NAME}.path"],
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)


def stop() -> None:
    run(["systemctl", "--user", "stop", f"{UNIT_NAME}.path"])
    run(["systemctl", "--user", "disable", f"{UNIT_NAME}.path"])
    info("stopped and disabled chezmoi-watch")


def main() -> None:
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "status":
            status()
            return
        if cmd == "stop":
            stop()
            return
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)

    files = get_managed_files()
    info(f"found {len(files)} managed files")
    for f in files:
        print(f"  {f}")

    path_unit, service_unit = generate_units(files)
    install_units(path_unit, service_unit)
    enable_and_start()

    info("watching for changes — save a dotfile and it auto-syncs back to the repo")


if __name__ == "__main__":
    main()
