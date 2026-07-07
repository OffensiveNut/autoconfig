#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = ["rich"]
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.ui import info, warn, ok, run

PACKAGES_FILE = Path(__file__).resolve().parent.parent / "packages.toml"


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


def detect_gpu_vendor() -> str | None:
    try:
        result = subprocess.run(
            ["lspci"], capture_output=True, text=True, timeout=10,
        )
        output = result.stdout.lower()
        if "nvidia" in output:
            return "nvidia"
        if "amd" in output or "advanced micro devices" in output:
            return "amd"
        if "intel" in output:
            return "intel"
    except FileNotFoundError:
        pass
    return None


VULKAN_DRIVERS: dict[str, list[str]] = {
    "nvidia": ["lib32-nvidia-utils"],
    "amd": ["lib32-vulkan-radeon"],
    "intel": ["lib32-vulkan-intel"],
}


def pacman_install_one(pkg: str) -> bool:
    result = subprocess.run(
        ["sudo", "pacman", "-S", "--noconfirm", "--needed", pkg],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return True
    if "provider" in result.stderr.lower() or "provider" in result.stdout.lower():
        warn(f"provider selection required for '{pkg}' — pre-installing vulkan driver")
        gpu = detect_gpu_vendor()
        if gpu:
            for dep in VULKAN_DRIVERS.get(gpu, []):
                subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "--needed", dep],
                               capture_output=True)
        result2 = subprocess.run(
            ["sudo", "pacman", "-S", "--noconfirm", "--needed", pkg],
            capture_output=True, text=True,
        )
        return result2.returncode == 0
    warn(f"failed to install '{pkg}': {result.stderr.strip() or result.stdout.strip()}")
    return False


def install_pacman(packages: list[str]) -> None:
    missing = [p for p in packages]
    if not missing:
        return
    info(f"installing {len(missing)} pacman packages (one at a time)")
    failed = []
    for pkg in missing:
        if pacman_install_one(pkg):
            info(f"  ✓ {pkg}")
        else:
            warn(f"  ✗ {pkg}")
            failed.append(pkg)
    if failed:
        warn(f"failed to install: {' '.join(failed)}")


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
