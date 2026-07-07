#!/bin/sh

set -eu

##############################
# Layer 0: Bootstrap
# Bare-metal system preparation
# POSIX sh only — no bashisms
##############################

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { printf "${GREEN}[INFO]${NC}  %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }
err()   { printf "${RED}[ERROR]${NC} %s\n" "$*"; }

detect_distro() {
    # shellcheck disable=SC1090
    . /etc/os-release
    case "$ID" in
        arch|artix|cachyos|endeavouros|manjaro)
            DISTRO="arch"
            PM_UPDATE="pacman -Syu --noconfirm"
            PM_INSTALL="pacman -S --noconfirm --needed"
            DEV_BASE="base-devel"
            ;;
        debian|ubuntu|pop|linuxmint)
            DISTRO="debian"
            PM_UPDATE="apt-get update"
            PM_INSTALL="apt-get install -y"
            DEV_BASE="build-essential"
            ;;
        *)
            err "unsupported distro: $ID"
            exit 1
            ;;
    esac
    info "detected distro family: $DISTRO ($ID)"
}

ensure_root() {
    if [ "$(id -u)" -ne 0 ]; then
        if command -v sudo >/dev/null 2>&1; then
            SUDO="sudo"
        else
            err "must be run as root (no sudo found)"
            exit 1
        fi
    else
        SUDO=""
    fi
}

update_packages() {
    info "updating package repositories"
    $SUDO $PM_UPDATE
}

install_baselines() {
    info "installing baseline packages ($DEV_BASE, git, curl)"
    # shellcheck disable=SC2086
    $SUDO $PM_INSTALL $DEV_BASE git curl
}

install_rust() {
    if command -v cargo >/dev/null 2>&1; then
        info "rust/cargo already installed, skipping"
        return
    fi
    info "installing rustup (rust/cargo toolchain)"
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    # shellcheck source=disable
    . "$HOME/.cargo/env"
}

install_uv() {
    if command -v uv >/dev/null 2>&1; then
        info "uv already installed, skipping"
        return
    fi
    info "installing standalone uv (astral)"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add to PATH for the remainder of the script
    if [ -f "$HOME/.local/bin/uv" ]; then
        export PATH="$HOME/.local/bin:$PATH"
    elif [ -f "$HOME/.cargo/bin/uv" ]; then
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
}

install_chezmoi() {
    if command -v chezmoi >/dev/null 2>&1; then
        info "chezmoi already installed, skipping"
        return
    fi
    info "installing chezmoi"
    case "${PM_INSTALL%% *}" in
        pacman) $SUDO pacman -S --noconfirm chezmoi ;;
        apt-get) $SUDO apt-get install -y chezmoi ;;
        dnf) $SUDO dnf install -y chezmoi ;;
        *) sh -c "$(curl -fsLS get.chezmoi.io)" ;;
    esac
}

install_yay() {
    if command -v yay >/dev/null 2>&1; then
        info "yay already installed, skipping"
        return
    fi
    if [ "$DISTRO" != "arch" ]; then
        return
    fi
    info "installing yay (AUR helper)"
    git clone --depth=1 https://aur.archlinux.org/yay.git /tmp/yay
    (cd /tmp/yay && makepkg -si --noconfirm --needed)
}

main() {
    detect_distro
    ensure_root
    update_packages
    install_baselines
    install_rust
    install_uv
    install_chezmoi
    install_yay

    info "bootstrap complete"
    info "next step: ./apply.sh"
}

main
