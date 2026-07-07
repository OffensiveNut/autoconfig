"""
Shared UI utilities for all Layer 2 scripts.

Provides consistent colored output and progress bar via `rich`.

Usage:
    from lib.ui import console, info, warn, ok, run, StepRunner
"""

import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

console = Console()

_IS_TTY = console.is_terminal


def info(msg: str) -> None:
    console.print(f"[bold blue]ℹ[/] {msg}")


def warn(msg: str) -> None:
    console.print(f"[bold yellow]⚠[/] [yellow]{msg}[/]")


def ok(msg: str) -> None:
    console.print(f"[bold green]✓[/] {msg}")


def run(cmd: list[str], capture_output: bool = False, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=capture_output, text=True, **kwargs)


def run_captured(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return run(cmd, capture_output=True, **kwargs)


class StepRunner:
    """Run steps with a progress bar for callables, or clean headers for scripts.

    When stdout is a TTY, `run()` uses a rich progress bar.
    When piped (e.g. as a subprocess of apply.py), both `run()` and
    `run_script()` fall back to simple sequential output.
    """

    def __init__(self, total: int = 0):
        self.total = total
        self._current = 0
        self._live: Live | None = None

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

        if total:
            self._task = self.progress.add_task("", total=total)
        else:
            self._task = None

    def __enter__(self):
        if _IS_TTY and self._task is not None:
            self._live = Live(self.progress, console=console, refresh_per_second=10)
            self._live.__enter__()
        return self

    def __exit__(self, *args):
        if self._live:
            self._live.__exit__(*args)

    def run(self, label: str, fn, *args, **kwargs):
        """Run a callable step against a single advancing progress bar."""
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

    def run_script(self, label: str, script_path: Path) -> bool:
        """Run a uv-based Python script with full terminal access.

        Prints a header before and status after the script runs.
        The script's stdout/stderr flows directly to the terminal,
        preserving interactivity (prompts, etc.).
        """
        self._current += 1
        prefix = f"[{self._current}/{self.total}] " if self.total else ""
        header = f"{prefix}{label}"

        if _IS_TTY:
            console.rule(f"[blue]{header}")
        else:
            info(header)

        result = subprocess.run(
            ["uv", "run", str(script_path)],
            check=False,
        )
        success = result.returncode == 0

        if success:
            ok(f"{header} done")
        else:
            warn(f"{header} failed (exit {result.returncode})")

        return success
