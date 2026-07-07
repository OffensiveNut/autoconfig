# System Automation Architecture (AI Agent Guidelines)

This repository holds my system automation logic. It is structured explicitly for an **AI Agent** or Co-pilot to generate, extend, and modify my environment scripts safely across different Linux distributions.

---

## 🏗️ The 3-Layer Design Strategy

Every automated workflow must be split into its proper layer to balance performance and maintainability:

[ Baremetal Setup ] ──> Layer 0: bootstrap.sh (POSIX sh)
│ (Detects distro, installs baseline tools & 'uv')
▼
Layer 1: Configuration (Chezmoi)
│ (Symlinks dotfiles, terminal tools, IDEs)
▼
Layer 2: Component-Based Engines (Python via uv)
(Each component handles its own installation/compilation)


1. **Layer 0: Bootstrap (`bootstrap.sh`)**
   * *Purpose:* Get the system bare-minimum ready.
   * *Stack:* Raw POSIX `sh`.
   * *Tasks:* Detect host OS, update package manager, install `git`, `curl`, development baselines, and bootstrap the standalone `uv` python engine.

2. **Layer 1: Configuration (`dot_chezmoi/`)**
   * *Purpose:* Track static state and configurations.
   * *Stack:* `chezmoi`
   * *Tasks:* Symlink shell files (`.zshrc`), desktop configs, and IDE states (Zed configs, Claude Code profiles).

3. **Layer 2: Component-Based Engines (`scripts/`)**
   * *Purpose:* Heavy compilation, hardware interfacing, and workspace orchestration.
   * *Stack:* Pure Python 3.12+ (run isolated via `uv run`).
   * *Structure:* **Highly modular.** Every major software stack or hardware component gets its own dedicated Python script containing all the logic needed to install, build, and verify that specific system.

---

## 🤖 Strict Rules for AI Generation

When creating or amending any code in this repository, you **must** follow these fundamental constraints:

### 1. Component Isolation
* Keep software workflows isolated. If asked to update how ROS or Docker is configured, all procedural logic, dependency lists, and system checks for that software must live entirely within its own file under `scripts/`.
* Use inline `uv` script metadata at the top of each file to declare the exact Python dependencies that specific script needs.

### 2. Distro-Agnostic Core Architecture
The automation framework must adapt seamlessly across clean installations on different base environments. **At a minimum, scripts must support Arch Linux (including Artix) and Debian/Ubuntu-based distributions.**
* **Package Management:** Do not hardcode package manager commands (`pacman` or `apt`). Abstract installations by checking which package manager is present, or utilize Python logic to branch depending on the detected OS family.
* **Dependencies:** Map package names correctly, as they frequently differ between ecosystems (e.g., `base-devel` on Arch vs. `build-essential` on Debian/Ubuntu).

### 3. Hard Idempotency Only
Every script block must safely support infinite execution runs. 
* Never issue blind install commands or overwrite files blindly. 
* **Always check state first:** verify if a binary is in the `$PATH`, if a systemd service is active, or if a kernel configuration signature (like `/sys/module/ec_master`) exists before performing an action.

### 4. Zero Global Environment Contamination
* Never execute global `pip install` commands or break system package-managed Python scopes. 
* All Python automation steps must run inside virtualized context windows via `uv run`. 

### 5. Dynamic Path Resolution
* Never hardcode explicit home paths. Use shell variable evaluations (`$HOME`) or Python abstractions (`Path.home()`) exclusively.

---

## 📁 Repository Layout Target

```text
.
├── bootstrap.sh               # Layer 0: Baremetal entrypoint (Distro detection)
├── dot_chezmoi/               # Layer 1: Dotfile source trees
│   ├── dot_zshrc              # Zsh configs & terminal hooks
│   └── private_dot_config/
│       ├── zed/               # Editor parameters
│       └── syncthing/         # Local syncing engine properties
└── scripts/                   # Layer 2: Dedicated Component Engines
    ├── docker_setup.py        # Installs daemon, configures groups & systemd runtime
    ├── ethercat_driver.py     # Checks kernel modules & compiles real-time master from source
    ├── ros_workspace.py       # Handles ROS distro selection, dependencies, & workspace sourcing
    ├── isaac_lab.py           # Sets up CUDA environments & Omni/Isaac simulation paths
    ├── syncthing_config.py    # Installs application & sets up local service files
    └── claude_code.py         # Installs Node/NPM baselines & configures AI tooling
