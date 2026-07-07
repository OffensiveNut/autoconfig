#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Zsh Environment Setup — Layer 2 Component Engine.

Installs:
  - Nerd Fonts (MesloLGS, JetBrainsMono) with FontAwesome icons
  - Atuin (shell history)
  - Zoxide (smarter cd)
  - Chezmoi (dotfile manager)
  - Zsh plugins (syntax-highlighting, autosuggestions, powerlevel10k)
"""

import shutil
import subprocess
from pathlib import Path


def is_installed(binary: str) -> bool:
    return shutil.which(binary) is not None


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kwargs)


def detect_pkg_manager() -> str:
    for mgr in ("pacman", "apt-get", "dnf", "zypper", "nix"):
        if shutil.which(mgr):
            return mgr
    raise RuntimeError("no supported package manager found")


def install_fonts() -> None:
    """
    Install MesloLGS Nerd Font and JetBrains Mono Nerd Font.

    These include FontAwesome glyphs required by Powerlevel10k.
    Skips if any of the font files already exist under ~/.local/share/fonts.
    """
    font_dir = Path.home() / ".local/share/fonts"
    fonts = {
        "MesloLGS": {
            "url": "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/Meslo.zip",
            "files": [
                "MesloLGS NF Regular.ttf",
                "MesloLGS NF Bold.ttf",
                "MesloLGS NF Italic.ttf",
                "MesloLGS NF Bold Italic.ttf",
            ],
        },
        "JetBrainsMono": {
            "url": "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.zip",
            "files": [
                "JetBrainsMono Nerd Font Regular.ttf",
                "JetBrainsMono Nerd Font Bold.ttf",
                "JetBrainsMono Nerd Font Italic.ttf",
                "JetBrainsMono Nerd Font Bold Italic.ttf",
            ],
        },
    }

    existing = set()
    if font_dir.is_dir():
        existing = {f.name for f in font_dir.iterdir() if f.is_file()}

    needs_install = {
        name: info
        for name, info in fonts.items()
        if not any(f in existing for f in info["files"])
    }
    if not needs_install:
        return

    font_dir.mkdir(parents=True, exist_ok=True)
    tmp = Path("/tmp/font_install")
    tmp.mkdir(parents=True, exist_ok=True)

    for name, info in needs_install.items():
        zip_path = tmp / f"{name}.zip"
        run(["curl", "-fsSL", "-o", str(zip_path), info["url"]])
        run(["unzip", "-q", "-o", str(zip_path), "-d", str(tmp / name)])
        for fname in info["files"]:
            src = tmp / name / fname
            if src.exists():
                shutil.copy2(src, font_dir / fname)

    run(["fc-cache", "-f"])


def install_atuin() -> None:
    if is_installed("atuin"):
        return
    run(["curl", "--proto", "=https", "--tlsv1.2", "-LsSf", "https://setup.atuin.sh", "-o", "/tmp/atuin.sh"])
    run(["sh", "/tmp/atuin.sh"])


def install_zoxide() -> None:
    if is_installed("zoxide"):
        return
    if is_installed("cargo"):
        run(["cargo", "install", "zoxide", "--locked"])
    else:
        run(["curl", "-fsSL", "https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh", "-o", "/tmp/zoxide.sh"])
        run(["sh", "/tmp/zoxide.sh"])


def install_chezmoi() -> None:
    if is_installed("chezmoi"):
        return
    mgr = detect_pkg_manager()
    if mgr == "pacman":
        run(["sudo", "pacman", "-S", "--noconfirm", "chezmoi"])
    elif mgr == "apt-get":
        run(["sudo", "apt-get", "install", "-y", "chezmoi"])
    elif mgr == "dnf":
        run(["sudo", "dnf", "install", "-y", "chezmoi"])
    else:
        run(["sh", "-c", "$(curl -fsLS get.chezmoi.io)"])


def apply_zsh_plugins() -> None:
    plugin_dir = Path.home() / ".config/zsh/plugin"
    plugins = {
        "zsh-syntax-highlighting": "https://github.com/zsh-users/zsh-syntax-highlighting.git",
        "zsh-autosuggestions": "https://github.com/zsh-users/zsh-autosuggestions.git",
        "powerlevel10k": "https://github.com/romkatv/powerlevel10k.git",
    }
    for name, url in plugins.items():
        target = plugin_dir / name
        if not target.is_dir():
            target.parent.mkdir(parents=True, exist_ok=True)
            run(["git", "clone", "--depth=1", url, str(target)])

    p10k = plugin_dir / "powerlevel10k"
    if (p10k / "Makefile").exists():
        run(["make", "-C", str(p10k), "pkg"])


def main() -> None:
    steps = [
        ("Nerd Fonts (MesloLGS, JetBrainsMono, FontAwesome)", install_fonts),
        ("Atuin (shell history)", install_atuin),
        ("Zoxide (smart cd)", install_zoxide),
        ("Chezmoi (dotfile manager)", install_chezmoi),
        ("Zsh plugins (syntax-highlighting, autosuggestions, p10k)", apply_zsh_plugins),
    ]
    for label, func in steps:
        func()

    print("chezmoi apply")


if __name__ == "__main__":
    main()
