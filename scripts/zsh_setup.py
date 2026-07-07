#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = ["rich"]
# ///
"""
Zsh Environment Setup — Layer 2 Component Engine.

Installs:
  - Nerd Fonts (MesloLGS, JetBrainsMono) with FontAwesome icons
  - Atuin (shell history)
  - Zoxide (smarter cd)
  - Eza (modern ls)
  - Ccat (cat with syntax highlighting)
  - Advcpmv (cp/mv with progress bar)
  - Zsh plugins (syntax-highlighting, autosuggestions, powerlevel10k)
  - Sets zsh as default login shell
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.ui import StepRunner, console, info, warn, ok, run


def detect_pkg_manager() -> str | None:
    for mgr in ("pacman", "apt-get", "dnf", "zypper"):
        if shutil.which(mgr):
            return mgr
    return None


def pkg_install(cmd: str) -> list[str]:
    mgr = detect_pkg_manager()
    if mgr == "pacman":
        return ["sudo", "pacman", "-S", "--noconfirm", cmd]
    if mgr == "apt-get":
        return ["sudo", "apt-get", "install", "-y", cmd]
    if mgr == "dnf":
        return ["sudo", "dnf", "install", "-y", cmd]
    return []


def install_fonts() -> None:
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
        name: data
        for name, data in fonts.items()
        if not any(f in existing for f in data["files"])
    }
    if not needs_install:
        ok("fonts already installed")
        return

    font_dir.mkdir(parents=True, exist_ok=True)
    tmp = Path("/tmp/font_install")
    tmp.mkdir(parents=True, exist_ok=True)

    for name, data in needs_install.items():
        zip_path = tmp / f"{name}.zip"
        run(["curl", "-fsSL", "-o", str(zip_path), data["url"]])
        run(["unzip", "-q", "-o", str(zip_path), "-d", str(tmp / name)])
        for fname in data["files"]:
            src = tmp / name / fname
            if src.exists():
                shutil.copy2(src, font_dir / fname)
    run(["fc-cache", "-f"])
    ok("fonts installed")


def install_atuin() -> None:
    if shutil.which("atuin"):
        ok("atuin already installed")
        return
    run(["curl", "--proto", "=https", "--tlsv1.2", "-LsSf", "https://setup.atuin.sh", "-o", "/tmp/atuin.sh"])
    run(["sh", "/tmp/atuin.sh"])
    ok("atuin installed")


def install_zoxide() -> None:
    if shutil.which("zoxide"):
        ok("zoxide already installed")
        return
    if shutil.which("cargo"):
        run(["cargo", "install", "zoxide", "--locked"])
    else:
        run(["curl", "-fsSL", "https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh", "-o", "/tmp/zoxide.sh"])
        run(["sh", "/tmp/zoxide.sh"])
    ok("zoxide installed")


def install_eza() -> None:
    if shutil.which("eza"):
        ok("eza already installed")
        return
    mgr = detect_pkg_manager()
    if mgr == "pacman":
        run(pkg_install("eza"))
    elif mgr == "apt-get":
        run(["sudo", "mkdir", "-p", "/etc/apt/keyrings"])
        run(["curl", "-fsSL", "https://raw.githubusercontent.com/eza-community/eza/main/deb.asc", "-o", "/tmp/eza.asc"])
        run(["sudo", "gpg", "--dearmor", "-o", "/etc/apt/keyrings/gierens.gpg", "/tmp/eza.asc"])
        run(["sh", "-c", "echo 'deb [signed-by=/etc/apt/keyrings/gierens.gpg] http://deb.gierens.de stable main' | sudo tee /etc/apt/sources.list.d/gierens.list >/dev/null"])
        run(["sudo", "chmod", "644", "/etc/apt/keyrings/gierens.gpg", "/etc/apt/sources.list.d/gierens.list"])
        run(["sudo", "apt-get", "update"])
        run(pkg_install("eza"))
    else:
        run(["cargo", "install", "eza", "--locked"])
    ok("eza installed")


def install_ccat() -> None:
    if shutil.which("ccat") and shutil.which("cless"):
        ok("ccat already installed")
        return
    arch = subprocess.run(["uname", "-m"], capture_output=True, text=True).stdout.strip()
    base = "https://github.com/owenthereal/ccat/releases/latest/download"
    suffix = "linux-amd64" if arch == "x86_64" else f"linux-{arch}"
    tmp = Path("/tmp/ccat")
    tmp.mkdir(parents=True, exist_ok=True)
    run(["curl", "-fsSL", "-o", str(tmp / "ccat.tgz"), f"{base}/ccat-{suffix}.tgz"])
    run(["tar", "-xzf", str(tmp / "ccat.tgz"), "-C", str(tmp)])
    extracted = list(tmp.iterdir())
    extracted_dir = None
    for p in extracted:
        if p.is_dir() and p.name.startswith("ccat-"):
            extracted_dir = p
            break
    if extracted_dir is None:
        extracted_dir = tmp
    for binary in ("ccat", "cless"):
        src = extracted_dir / binary
        if src.exists():
            run(["sudo", "cp", str(src), f"/usr/local/bin/{binary}"])
    ok("ccat installed")


def install_advcpmv() -> None:
    if Path("/usr/local/bin/advcp").exists() and Path("/usr/local/bin/advmv").exists():
        ok("advcpmv already installed")
        return
    tmp = Path("/tmp/advcpmv")
    tmp.mkdir(parents=True, exist_ok=True)
    script = tmp / "install.sh"
    run(["curl", "-fsSL", "https://raw.githubusercontent.com/jarun/advcpmv/master/install.sh", "-o", str(script)])
    run(["sh", str(script)], cwd=str(tmp))
    if (tmp / "advcp").exists():
        run(["sudo", "mv", str(tmp / "advcp"), "/usr/local/bin/advcp"])
    if (tmp / "advmv").exists():
        run(["sudo", "mv", str(tmp / "advmv"), "/usr/local/bin/advmv"])
    ok("advcpmv installed")


def apply_zsh_plugins() -> None:
    plugin_dir = Path.home() / ".config/zsh/plugin"
    cloned = 0
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
            cloned += 1

    p10k = plugin_dir / "powerlevel10k"
    if (p10k / "Makefile").exists():
        run(["make", "-C", str(p10k), "pkg"])
    info(f"plugins: {cloned} cloned, {len(plugins) - cloned} cached")


def install_zsh_pkg() -> None:
    if shutil.which("zsh"):
        ok("zsh already installed")
        return
    cmd = pkg_install("zsh")
    if cmd:
        run(cmd)
        ok("zsh installed")
    else:
        warn("no package manager found — install zsh manually")


def set_default_shell() -> None:
    zsh_path = shutil.which("zsh")
    if not zsh_path:
        warn("zsh not found, can't set as default shell")
        return
    result = subprocess.run(["chsh", "-s", zsh_path])
    if result.returncode == 0:
        info("zsh set as default login shell (log out and back in)")
    else:
        warn(f"failed to set zsh as default shell")


def main() -> None:
    steps = [
        ("Nerd Fonts (MesloLGS, JetBrainsMono, FontAwesome)", install_fonts),
        ("Atuin (shell history)", install_atuin),
        ("Zoxide (smart cd)", install_zoxide),
        ("Eza (modern ls)", install_eza),
        ("Ccat (highlighted cat/less)", install_ccat),
        ("Advcpmv (cp/mv progress)", install_advcpmv),
        ("Zsh package", install_zsh_pkg),
        ("Zsh plugins", apply_zsh_plugins),
        ("Set zsh as default shell", set_default_shell),
    ]

    with StepRunner(total=len(steps)) as runner:
        for label, func in steps:
            runner.run(label, func)

    console.print()
    console.rule("[bold green]zsh setup complete[/]")


if __name__ == "__main__":
    main()
