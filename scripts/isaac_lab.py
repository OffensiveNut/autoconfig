#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = ["rich"]
# ///
"""
Isaac Lab Setup — Layer 2 Component Engine.

Ubuntu-only. Installs Isaac Sim + Isaac Lab inside a uv-managed virtual
environment. Runs user-interactive steps (EULA acceptance, ~10 min pull).
Not auto-installed — pass --install to run:

  uv run scripts/isaac_lab.py --install
"""

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.ui import info, warn, ok, run


def _is_debian() -> bool:
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("ID="):
                    return line.split("=", 1)[1].strip().strip("\"") in ("ubuntu", "debian", "pop", "linuxmint")
    except FileNotFoundError:
        pass
    return False


if not _is_debian():
    ok("Isaac Lab requires Debian/Ubuntu — skipping")
    sys.exit(0)


def install_isaac() -> None:

    home = Path.home()
    workspace = home / "Projects/isaac"
    env_dir = workspace / "env_isaaclab"
    env_python = env_dir / "bin/python"
    isaac_lab_dir = workspace / "IsaacLab"

    if (env_dir / "bin/activate").exists():
        info(f"Isaac Lab environment already exists at {env_dir}")

    workspace.mkdir(parents=True, exist_ok=True)

    info("creating uv virtual environment (Python 3.11)")
    run(["uv", "venv", "--python", "3.11", "--seed", str(env_dir)])

    info("upgrading pip")
    run([str(env_python), "-m", "pip", "install", "--upgrade", "pip"])

    info("installing Isaac Sim pip packages (this may take a while)")
    run([
        str(env_python), "-m", "pip", "install",
        "isaacsim[all,extscache]==5.1.0",
        "--extra-index-url", "https://pypi.nvidia.com",
    ])

    info("installing CUDA-enabled PyTorch")
    run([
        str(env_python), "-m", "pip", "install", "-U",
        "torch==2.7.0", "torchvision==0.22.0",
        "--index-url", "https://download.pytorch.org/whl/cu128",
    ])

    if not isaac_lab_dir.is_dir():
        info("cloning Isaac Lab repository")
        run([
            "git", "clone",
            "https://github.com/isaac-sim/IsaacLab.git",
            str(isaac_lab_dir),
        ])
    else:
        info("Isaac Lab repository already cloned")

    info("installing apt dependencies for Isaac Lab")
    run(["sudo", "apt-get", "install", "-y", "cmake", "build-essential"])

    info("running Isaac Lab install script")
    install_script = isaac_lab_dir / "isaaclab.sh"
    run(["bash", str(install_script), "--install"])

    info("Isaac Lab installation complete")
    info(f"activate:  source {env_dir}/bin/activate")
    info("first run: isaacsim (will pull extensions ~10 min + EULA prompt)")
    info("           reply 'Yes' to the NVIDIA Omniverse EULA")


def main() -> None:
    if "--install" not in sys.argv:
        print("Usage: uv run scripts/isaac_lab.py --install")
        print()
        print("This script installs Isaac Sim 5.x + Isaac Lab in ~/Projects/isaac/")
        print("Ubuntu/Debian only. Requires CUDA-capable GPU.")
        print()
        print("Steps performed:")
        print("  1. Create uv venv (Python 3.11) at ~/Projects/isaac/env_isaaclab")
        print("  2. Install isaacsim pip package from pypi.nvidia.com")
        print("  3. Install PyTorch 2.7.0 with CUDA 12.8")
        print("  4. Clone IsaacLab repo to ~/Projects/isaac/IsaacLab")
        print("  5. Run IsaacLab's internal install script")
        print()
        print("After install, first run triggers ~10 min extension pull + EULA prompt.")
        return

    install_isaac()


if __name__ == "__main__":
    main()
