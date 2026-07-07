#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = ["rich"]
# ///
"""Layer orchestrator — chezmoi apply, then run all scripts/ with headers."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from lib.ui import console, info, warn, ok

CHEZMOI_SOURCE = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "chezmoi"


def setup_source_link() -> None:
    source = Path("dot_chezmoi").resolve()
    target = CHEZMOI_SOURCE.resolve()
    if target == source:
        return
    if target.is_dir() and not target.is_symlink():
        target.rename(target.parent / f"{target.name}.bak")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    target.symlink_to(source)


def run_script(script: Path, step: int, total: int) -> None:
    label = script.stem.replace("_", " ").title()
    console.rule(f"[blue][{step}/{total}] {label}")
    env = os.environ | {"AUTOCONFIG_ORCHESTRATED": "1"}
    r = subprocess.run(["uv", "run", str(script)], env=env)
    (ok if r.returncode == 0 else warn)(f"[{step}/{total}] {label} " + ("done" if r.returncode == 0 else f"failed (exit {r.returncode})"))
    console.print()


def main() -> None:
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    args = [Path(a) for a in sys.argv[1:] if not a.startswith("--")]

    for prog in ("chezmoi", "uv"):
        if not shutil.which(prog):
            warn(f"{prog} not found — run bootstrap.sh first")
            sys.exit(1)

    setup_source_link()

    if "--re-add" in flags:
        subprocess.run(["chezmoi", "re-add"])
        return

    if "--layer2" not in flags:
        info("applying chezmoi dotfiles")
        subprocess.run(["chezmoi", "apply"], check=True)

        # Strip ephemeral ConfigDialog sections and symlink plasma6 configs
        plasma_dir = Path.home() / ".config/plasma6"
        if plasma_dir.is_dir():
            for f in plasma_dir.iterdir():
                text = f.read_text().splitlines()
                out = []
                skip = False
                for line in text:
                    if line.startswith("[") and line.endswith("][ConfigDialog]"):
                        skip = True
                        continue
                    if line.startswith("[") and not "ConfigDialog" in line:
                        skip = False
                    if not skip:
                        out.append(line)
                f.write_text("\n".join(out) + "\n")

                target = Path.home() / ".config" / f.name
                if not target.exists() and not target.is_symlink():
                    target.symlink_to(f)
                    info(f"linked ~/.config/plasma6/{f.name}")

        # Symlink repo assets into home so configs can reference them
        assets_dir = Path("assets").resolve()
        if assets_dir.is_dir():
            link = Path.home() / ".local/share/autoconfig-assets"
            if not link.exists():
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(assets_dir)
                info(f"linked assets → ~/.local/share/autoconfig-assets")
        console.print()

    scripts = args or sorted(Path("scripts").glob("*.py"))
    for i, s in enumerate(scripts, start=1):
        run_script(s, i, len(scripts))

    console.rule("[bold green]done")


if __name__ == "__main__":
    main()
