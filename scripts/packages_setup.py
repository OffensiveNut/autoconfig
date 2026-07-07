#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
General software installer — reads packages.toml and installs per distro.

Usage:
  uv run scripts/packages_setup.py            # install all managers for detected distro
  uv run scripts/packages_setup.py pacman      # install only pacman section
  uv run scripts/packages_setup.py yay apt     # install those managers only
"""

import shutil
import subprocess
import sys
import tomllib
from pathlib import Path


PACKAGES_FILE = Path(__file__).resolve().parent.parent / "packages.toml"


def info(msg: str) -> None:
    print(f"[INFO]  {msg}")


def warn(msg: str) -> None:
    print(f"[WARN]  {msg}")


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kwargs)


def detect_distro() -> str | None:
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("ID="):
                    val = line.split("=", 1)[1].strip().strip("\"")
                    if val in ("arch", "artix", "cachyos", "endeavouros", "manjaro"):
                        return "arch"
                    if val in ("debian", "ubuntu", "pop", "linuxmint"):
                        return "debian"
    except FileNotFoundError:
        pass
    return None


def load_packages() -> dict:
    with open(PACKAGES_FILE, "rb") as f:
        return tomllib.load(f)


def is_installed(binary: str) -> bool:
    return shutil.which(binary) is not None


def install_pacman(packages: list[str]) -> None:
    missing = [p for p in packages if not is_installed(p)]
    if not missing:
        info("all pacman packages already installed")
        return
    info(f"installing {len(missing)} pacman packages")
    run(["sudo", "pacman", "-S", "--noconfirm", "--needed", *missing])


def install_yay(packages: list[str]) -> None:
    if not is_installed("yay"):
        warn("yay not found — run bootstrap.sh first")
        return
    missing = [p for p in packages]
    if not missing:
        return
    info(f"installing {len(missing)} AUR packages via yay")
    run(["yay", "-S", "--noconfirm", "--needed", *missing])


def install_apt(packages: list[str]) -> None:
    missing = [p for p in packages]
    if not missing:
        return
    info(f"installing {len(missing)} apt packages")
    run(["sudo", "apt-get", "install", "-y", *missing])


MANAGERS = {
    "pacman": install_pacman,
    "yay": install_yay,
    "apt": install_apt,
}


def main() -> None:
    distro = detect_distro()
    if distro is None:
        warn("unsupported distro — skipping package installation")
        return

    all_packages = load_packages()
    distro_config = all_packages.get(distro, {})

    requested = sys.argv[1:] if len(sys.argv) > 1 else list(distro_config.keys())

    for mgr in requested:
        if mgr not in distro_config:
            warn(f"no '{mgr}' section for distro '{distro}' in packages.toml")
            continue
        install_fn = MANAGERS.get(mgr)
        if install_fn is None:
            warn(f"no installer implemented for manager '{mgr}'")
            continue
        pkgs = distro_config[mgr].get("packages", [])
        if not pkgs:
            info(f"no packages listed for '{mgr}'")
            continue
        install_fn(pkgs)

    info("package installation complete")


if __name__ == "__main__":
    main()
