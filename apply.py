#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = ["rich"]
# ///
"""
apply.py — Layer Orchestrator

Links ~/.local/share/chezmoi → dot_chezmoi/ for two-way sync, applies dotfiles,
then runs Layer 2 component scripts with a unified progress bar.

Usage:
  uv run apply.py                             # apply + all scripts
  uv run apply.py scripts/foo.py              # apply + specific scripts
  uv run apply.py --layer2                    # skip apply, run all scripts
  uv run apply.py --layer2 scripts/foo.py
  uv run apply.py --re-add                    # re-add + apply + all scripts
  uv run apply.py --re-add ~/.zshrc
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import lib.ui
from lib.ui import StepRunner, console, info, warn, ok


REPO_SOURCE = Path("dot_chezmoi").resolve()
CHEZMOI_SOURCE = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "chezmoi"


def check_deps() -> None:
    if not shutil.which("chezmoi"):
        warn("chezmoi not found — run bootstrap.sh first")
        sys.exit(1)
    if not shutil.which("uv"):
        warn("uv not found — run bootstrap.sh first")
        sys.exit(1)


def setup_source_link() -> None:
    target = CHEZMOI_SOURCE.resolve()
    source = REPO_SOURCE

    if target == source:
        return
    if target.is_dir() and not target.is_symlink():
        backup = target.parent / f"{target.name}.bak"
        warn(f"backing up existing chezmoi source to {backup}")
        target.rename(backup)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    target.symlink_to(source)
    info("linked chezmoi source → dot_chezmoi/")


def apply_chezmoi() -> None:
    info("applying chezmoi dotfiles")
    subprocess.run(["chezmoi", "apply"], check=True)


def re_add_chezmoi(files: list[str] | None = None) -> None:
    cmd = ["chezmoi", "re-add"]
    if files:
        cmd.extend(files)
        info(f"pulling {' '.join(files)} back to repo")
    else:
        info("pulling all changes back to repo")
    subprocess.run(cmd, check=True)
    info("run 'git diff' to review, then commit")


def discover_scripts() -> list[Path]:
    scripts_dir = Path("scripts")
    return sorted(scripts_dir.glob("*.py"))


def main() -> None:
    check_deps()
    setup_source_link()

    re_add = False
    re_add_files: list[str] = []
    layer2_only = False
    script_args: list[str] = []
    parsing_re_add_files = False

    for arg in sys.argv[1:]:
        if arg == "--re-add":
            re_add = True
            parsing_re_add_files = True
        elif arg == "--layer2":
            layer2_only = True
            parsing_re_add_files = False
        elif arg == "--":
            parsing_re_add_files = False
        elif parsing_re_add_files and re_add:
            re_add_files.append(arg)
        else:
            script_args.append(arg)

    if re_add:
        re_add_chezmoi(re_add_files if re_add_files else None)
        console.print()

    if not layer2_only:
        apply_chezmoi()
        console.print()

    scripts_to_run: list[Path] = []
    if script_args:
        for a in script_args:
            p = Path(a)
            if p.exists():
                scripts_to_run.append(p)
            else:
                warn(f"script not found: {a}")
    elif re_add and not script_args:
        pass
    else:
        scripts_to_run = discover_scripts()

    if scripts_to_run:
        with StepRunner(total=len(scripts_to_run)) as steps:
            for script in scripts_to_run:
                label = script.stem.replace("_", " ").title()
                steps.run_script(label, script)

    console.rule("[bold green]done")


if __name__ == "__main__":
    main()
