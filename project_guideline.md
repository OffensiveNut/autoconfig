# System Automation Architecture (AI Agent Guidelines)

This repository holds my system automation logic. Designed for an **AI Agent** to generate, extend, and modify environment scripts across Linux distributions.

---

## The 3-Layer Strategy

```
./bootstrap.sh    ──►  Layer 0: Baremetal (POSIX sh)
                            Distro detection, git/curl/uv/chezmoi

./apply.sh        ──►  Layer 1: Dotfiles (chezmoi)
                            Symlinks .zshrc, .p10k.zsh, .config/*

                    ──►  Layer 2: Components (Python via uv)
                            scripts/*.py — auto-discovered, each self-contained
```

**Layer 0 — Bootstrap (`bootstrap.sh`)**
- Raw POSIX `sh`, run once on a fresh system.
- Detects distro (`/etc/os-release`), updates packages, installs `git`/`curl`/`base-devel`/`build-essential`, bootstraps `uv`, installs `chezmoi`.
- Idempotent — safe to re-run.

**Layer 1 — Dotfiles (`dot_chezmoi/`)**
- Chezmoi source directory. Every file with a `dot_`/`private_`/`executable_` prefix is discovered automatically by chezmoi.
- Applied via `./apply.sh` or `chezmoi apply --source "$PWD/dot_chezmoi"`.

**Layer 2 — Components (`scripts/`)**
- Every `.py` file is a standalone component engine run via `uv run`.
- Auto-discovered by `./apply.sh` — no manifest to update.
- Each script declares its deps in inline uv metadata (`# /// script`).

---

## How to Add Stuff

### New dotfile
Drop a file in `dot_chezmoi/` with the right chezmoi prefix:
```
dot_chezmoi/dot_gitconfig          → ~/.gitconfig
dot_chezmoi/private_dot_config/foo/bar → ~/.config/foo/bar (mode 600)
```
No registration needed — `./apply.sh` picks it up.

### New component script
Create `scripts/my_thing.py` with a uv shebang:
```python
#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = ["requests"]
# ///
"""Install my thing."""
```
`./apply.sh` discovers and runs it automatically.

---

## Strict Rules

1. **Isolation** — Each component is its own file under `scripts/`. No shared state.
2. **Distro-agnostic** — Support Arch (Artix, CachyOS, EndeavourOS, Manjaro) and Debian/Ubuntu (Pop, Mint). Abstract package manager commands.
3. **Idempotent** — Check state first (`command -v`, `Path.exists()`, `systemctl is-active`). Never blindly install or overwrite.
4. **No global pip** — All Python runs inside `uv run` virtualized contexts.
5. **Dynamic paths** — Use `$HOME` or `Path.home()`, never hardcode `/home/username`.

---

## Repository Layout

```
.
├── apply.sh                # Orchestrator: Layer 1 → Layer 2 (auto-discovery)
├── bootstrap.sh            # Layer 0: system prep + yay
├── packages.toml           # Per-distro package lists (pacman/aur/apt)
├── dot_chezmoi/            # Layer 1: chezmoi source
│   ├── dot_zshrc
│   ├── dot_p10k.zsh
│   └── private_dot_config/{kitty,zed,syncthing}/
├── scripts/                # Layer 2: component engines
│   ├── packages_setup.py   # Reads packages.toml, installs per distro
│   ├── zsh_setup.py        # Fonts, atuin, zoxide, eza, ccat, advcpmv, zsh plugins
│   ├── isaac_lab.py        # Ubuntu-only Isaac Sim/Lab (opt-in --install)
│   └── ...                 # Drop new .py files here
└── project_guideline.md    # This file
```
