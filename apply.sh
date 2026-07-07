#!/bin/sh
set -eu

##############################
# apply.sh — Layer Orchestrator
# Applies chezmoi dotfiles (Layer 1), then runs any number of
# component scripts (Layer 2).  Auto-discovers scripts/ by default.
#
# Usage:
#   ./apply.sh                   # chezmoi + all scripts
#   ./apply.sh scripts/foo.py    # chezmoi + specific script(s)
#   ./apply.sh --layer2          # skip chezmoi, run all scripts
#   ./apply.sh --layer2 scripts/foo.py
##############################

LAYER1_SOURCE="$PWD/dot_chezmoi"

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

apply_chezmoi() {
    info "Layer 1 — applying chezmoi dotfiles"
    chezmoi apply --source "$LAYER1_SOURCE"
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

    LAYER2_ONLY=false
    SCRIPT_ARGS=""

    for arg in "$@"; do
        case "$arg" in
            --layer2) LAYER2_ONLY=true ;;
            *) SCRIPT_ARGS="$SCRIPT_ARGS $arg" ;;
        esac
    done

    if [ "$LAYER2_ONLY" = false ]; then
        apply_chezmoi
        printf '\n'
    fi

    if [ -n "$SCRIPT_ARGS" ]; then
        for script in $SCRIPT_ARGS; do
            run_script "$script"
        done
    else
        for script in scripts/*.py; do
            [ -f "$script" ] || continue
            run_script "$script"
        done
    fi

    info "done"
}

main "$@"
