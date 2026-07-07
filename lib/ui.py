"""
Shared UI utilities for all Layer 2 scripts.

Usage:
    from lib.ui import console, info, warn, ok, run, StepRunner
"""

import os
import subprocess

from rich.console import Console
from rich.live import Live
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

console = Console()

_IS_TTY = console.is_terminal and not os.environ.get("AUTOCONFIG_ORCHESTRATED")


def info(msg: str) -> None:
    console.print(f"[bold blue]ℹ[/] {msg}")


def warn(msg: str) -> None:
    console.print(f"[bold yellow]⚠[/] [yellow]{msg}[/]")


def ok(msg: str) -> None:
    console.print(f"[bold green]✓[/] {msg}")


def run(cmd: list[str], capture_output: bool = False, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=capture_output, text=True, **kwargs)


class StepRunner:
    """Single advancing progress bar for multi-step functions (e.g. zsh_setup.py).

    Uses rich Live when in a TTY; falls back to simple ok/warn per step
    when AUTOCONFIG_ORCHESTRATED is set.
    """

    def __init__(self, total: int = 0):
        columns = [
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
        ]
        if _IS_TTY:
            self.progress = Progress(*columns, console=console)
        else:
            self.progress = Progress(*columns, console=console, disable=True)
        self._task = self.progress.add_task("", total=total) if total else None
        self._live: Live | None = None

    def __enter__(self):
        if _IS_TTY and self._task is not None:
            self._live = Live(self.progress, console=console, refresh_per_second=10)
            self._live.__enter__()
        return self

    def __exit__(self, *args):
        if self._live:
            self._live.__exit__(*args)

    def run(self, label: str, fn, *args, **kwargs):
        """Run a step, advancing the single progress bar if present."""
        if self._task is not None:
            self.progress.update(self._task, description=f"[cyan]{label}...")
            if self._live:
                self._live.update(self.progress)
        try:
            fn(*args, **kwargs)
        except Exception as e:
            if self._task is not None:
                self.progress.update(self._task, description=f"[red]{label} failed[/]", advance=1)
                if self._live:
                    self._live.update(self.progress)
            if not _IS_TTY:
                warn(f"{label}: {e}")
            return False
        if self._task is not None:
            self.progress.update(self._task, advance=1)
            if self._live:
                self._live.update(self.progress)
        if not _IS_TTY:
            ok(f"{label} done")
        return True
