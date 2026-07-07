#!/bin/sh
set -eu

##############################
# apply.sh — Layer Orchestrator
#
# Manages dotfiles and runs component installers.
# Links ~/.local/share/chezmoi → dot_chezmoi/ for two-way sync.
#
# Usage:
#   ./apply.sh                                 # apply + all scripts
#   ./apply.sh --layer2                        # skip apply, run all scripts
#   ./apply.sh --layer2 scripts/foo.py         # skip apply, run specific scripts
#   ./apply.sh scripts/foo.py                  # apply + specific scripts
#   ./apply.sh --re-add                        # re-add + apply + all scripts
#   ./apply.sh --re-add ~/.zshrc               # re-add file + apply + all scripts
#   ./apply.sh --re-add -- layer2 scripts/foo.py
##############################

REPO_SOURCE="$PWD/dot_chezmoi"
CHEZMOI_SOURCE="${XDG_DATA_HOME:-$HOME/.local/share}/chezmoi"

info()  { printf '[INFO]  %s\n' "$*"; }
warn()  { printf '[WARN]  %s\n' "$*"; }
err()   { printf '[ERROR] %s\n' "$*" >&2; }

check_deps() {
    if ! command -v chezmoi >/dev/null 2>&1; then
        err "chezmoi not found — run bootstrap.sh first"
        exit 1
    fi
    if ! command -v uv >/dev/null 2>&1; then
        err "uv not found — run bootstrap.sh first"
        exit 1
    fi
}

setup_source_link() {
    if [ "$(readlink -f "$CHEZMOI_SOURCE" 2>/dev/null)" = "$(readlink -f "$REPO_SOURCE")" ]; then
        return
    fi
    if [ -e "$CHEZMOI_SOURCE" ] && [ ! -L "$CHEZMOI_SOURCE" ]; then
        warn "backing up existing chezmoi source to ${CHEZMOI_SOURCE}.bak"
        mv "$CHEZMOI_SOURCE" "${CHEZMOI_SOURCE}.bak"
    fi
    mkdir -p "$(dirname "$CHEZMOI_SOURCE")"
    ln -sfn "$REPO_SOURCE" "$CHEZMOI_SOURCE"
    info "linked chezmoi source to repo"
}

apply_chezmoi() {
    info "Layer 1 — applying chezmoi dotfiles"
    chezmoi apply
}

re_add_chezmoi() {
    if [ $# -gt 0 ]; then
        info "pulling system changes back to repo: $*"
        chezmoi re-add "$@"
    else
        info "pulling all system changes back to repo"
        chezmoi re-add
    fi
    info "run 'git status' to see what changed"
}

run_script() {
    script="$1"
    if [ ! -f "$script" ]; then
        warn "script not found: $script"
        return
    fi
    info "Layer 2 — $(basename "$script" .py)"
    uv run "$script"
    printf '\n'
}

main() {
    check_deps
    setup_source_link

    RE_ADD=false
    PASSED_DASHLINE=false
    LAYER2_ONLY=false
    RE_ADD_FILES=""
    SCRIPT_ARGS=""

    for arg in "$@"; do
        case "$arg" in
            --re-add) RE_ADD=true ;;
            --) PASSED_DASHLINE=true ;;
            --layer2) LAYER2_ONLY=true ;;
            *)
                if [ "$RE_ADD" = true ] && [ "$PASSED_DASHLINE" = false ]; then
                    RE_ADD_FILES="$RE_ADD_FILES $arg"
                else
                    SCRIPT_ARGS="$SCRIPT_ARGS $arg"
                fi
                ;;
        esac
    done

    if [ "$RE_ADD" = true ]; then
        # shellcheck disable=SC2086
        re_add_chezmoi $RE_ADD_FILES
        printf '\n'
    fi

    if [ "$LAYER2_ONLY" = false ]; then
        apply_chezmoi
        printf '\n'
    fi

    if [ -n "$SCRIPT_ARGS" ]; then
        for script in $SCRIPT_ARGS; do
            run_script "$script"
        done
    elif [ "$RE_ADD" = false ] && [ "$LAYER2_ONLY" = false ]; then
        for script in scripts/*.py; do
            [ -f "$script" ] || continue
            run_script "$script"
        done
    elif [ "$LAYER2_ONLY" = true ]; then
        for script in scripts/*.py; do
            [ -f "$script" ] || continue
            run_script "$script"
        done
    fi

    info "done"
}

main "$@"
