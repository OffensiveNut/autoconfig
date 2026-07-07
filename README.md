# arch-autoconfig

Automated system setup for Arch and Debian-based Linux distros.

## Quick Start

```sh
# 1. Bootstrap the system (git, curl, uv, chezmoi, yay)
./bootstrap.sh

# 2. Apply dotfiles and run all component installers
./apply.sh
```

## Workflow

```
bootstrap.sh  →  apply.sh  →  apply.py
(Layer 0)                     ├─ chezmoi apply    (Layer 1 — dotfiles)
                              └─ uv run scripts/*.py  (Layer 2 — components)
```

`apply.sh` is a thin POSIX wrapper that delegates to `apply.py`, the Python
orchestrator. All Layer 2 scripts share a single rich progress bar and
consistent colored output via `lib/ui.py`.

## Per-layer guide

### Layer 0 — `bootstrap.sh`

Run once on a fresh system. Detects your distro and installs the essentials:
- `git`, `curl`, build tools (`base-devel` / `build-essential`)
- `uv` (Python package manager)
- `chezmoi` (dotfile manager)
- `yay` (AUR helper, Arch only)

Idempotent — safe to re-run.

### Layer 1 — `dot_chezmoi/`

Chezmoi source directory. `./apply.sh` links `~/.local/share/chezmoi` → this
repo's `dot_chezmoi/` for two-way sync.

| File | Installed to |
|------|-------------|
| `dot_chezmoi/dot_zshrc` | `~/.zshrc` |
| `dot_chezmoi/dot_p10k.zsh` | `~/.p10k.zsh` |
| `dot_chezmoi/private_dot_config/kitty/kitty.conf` | `~/.config/kitty/kitty.conf` |

**Two-way sync:**

```sh
# Repo → system (apply dotfiles)
./apply.sh

# System → repo (pull changes back)
./apply.sh --re-add
./apply.sh --re-add ~/.zshrc
```

**Auto-watch** — automatically sync edits back to the repo in real time:

```sh
uv run scripts/setup_watch.py          # start watching (runs as a systemd user service)
uv run scripts/setup_watch.py status   # check if it's running
uv run scripts/setup_watch.py stop     # stop watching
```

To add a new dotfile, just drop it in `dot_chezmoi/` with the right prefix:
- `dot_` → `.` (e.g. `dot_gitconfig` → `~/.gitconfig`)
- `private_dot_config/` → `~/.config/` (mode 0700)

### Layer 2 — `scripts/`

Component installers. Each is a standalone Python script run via `uv run`.
`./apply.sh` auto-discovers all `scripts/*.py` and runs them under a single
progress bar with rich colored output.

All scripts share a common UI library at `lib/ui.py` that provides:

| Export | Purpose |
|--------|---------|
| `info()` | Blue ℹ info message |
| `warn()` | Yellow ⚠ warning |
| `ok()` | Green ✓ success |
| `run()` | Subprocess runner (with live output) |
| `StepRunner` | Context manager for progress bars |

| Script | What it installs |
|--------|-----------------|
| `zsh_setup.py` | Nerd Fonts (MesloLGS, JetBrainsMono), atuin, zoxide, eza, ccat, advcpmv, zsh plugins |
| `packages_setup.py` | General software from `packages.toml` (discord, steam, browser, etc.) |
| `isaac_lab.py` | Isaac Sim + Isaac Lab (Ubuntu only, opt-in with `--install`) |

Run selectively:
```sh
uv run scripts/zsh_setup.py           # single script (own progress bar)
uv run scripts/packages_setup.py yay  # AUR packages only
./apply.sh scripts/foo.py             # chezmoi + specific script
./apply.sh --layer2                   # skip chezmoi, run all scripts
./apply.sh --layer2 scripts/bar.py    # skip chezmoi, run one script
```

## Package management

Edit `packages.toml` to add or remove software per distro:

```toml
[arch.pacman]
packages = ["discord", "steam", ...]

[arch.yay]
packages = ["brave-bin", "librewolf-bin", ...]

[debian.apt]
packages = ["discord", "steam-installer", ...]
```

Then run `uv run scripts/packages_setup.py` to apply changes.

## Adding your own component

1. Create `scripts/my_thing.py`:
```python
#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = ["rich"]
# ///
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.ui import info, warn, ok, run

"""Install my thing."""
```
2. `./apply.sh` picks it up automatically. No registration needed.

## Supported distros

- **Arch Linux**, Artix, CachyOS, EndeavourOS, Manjaro
- **Debian**, Ubuntu, Pop!_OS, Linux Mint

## Design

Three layers, each independent:

| Layer | Stack | Responsibility |
|-------|-------|---------------|
| 0 | POSIX sh | Distro detection, system baselines, toolchain |
| 1 | chezmoi | Dotfile symlinks |
| 2 | Python/uv | Component installation, compilation, config |
