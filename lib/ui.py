"""
Shared UI utilities for all Layer 2 scripts.

Provides consistent colored output and progress bar via `rich`.

Usage:
    from lib.ui import console, info, warn, ok, run, StepRunner
"""

import os
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.layout import Layout
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
    """Run steps with a live progress bar + output panel.

    Falls back to sequential output when stdout is not a TTY
    (e.g. when running as a subprocess of apply.py).
    """

    def __init__(self, show_output: bool = True):
        self.show_output = show_output
        self._log: list[str] = []
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

    def log(self, text: str) -> None:
        self._log.append(text)

    def _build_renderable(self):
        layout = Layout()
        layout.split_column(
            Layout(Panel(self.progress, border_style="blue"), size=4),
            Layout(Panel(
                "\n".join(self._log[-50:]) if self._log else "[dim]no output yet[/]",
                title="Output",
                border_style="dim",
            )),
        )
        return layout

    def __enter__(self):
        if _IS_TTY:
            self._live = Live(
                self._build_renderable(),
                console=console,
                refresh_per_second=10,
            )
            self._live.__enter__()
        return self

    def __exit__(self, *args):
        if self._live:
            self._live.__exit__(*args)

    def _refresh(self):
        if self._live:
            self._live.update(self._build_renderable())

    def run(self, label: str, fn, *args, **kwargs):
        """Run a callable step."""
        task = self.progress.add_task(f"[cyan]{label}...", total=1)
        self._refresh()
        try:
            fn(*args, **kwargs)
        except Exception as e:
            self.progress.update(task, description=f"[red]{label} failed[/]", completed=1)
            self._log.append(f"[red]✗ {label}: {e}[/]")
            self._refresh()
            if not _IS_TTY:
                warn(f"{label}: {e}")
            return False
        self.progress.update(task, completed=1)
        self._log.append(f"[green]✓ {label} done[/]")
        self._refresh()
        if not _IS_TTY:
            ok(f"{label} done")
        return True

    def run_script(self, label: str, script_path: Path) -> bool:
        """Run a uv-based Python script, streaming output live."""
        task = self.progress.add_task(f"[cyan]{label}...", total=1)
        self._refresh()

        process = subprocess.Popen(
            ["uv", "run", str(script_path)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )

        assert process.stdout is not None
        for line in iter(process.stdout.readline, ""):
            stripped = line.rstrip("\n\r")
            if stripped:
                self._log.append(stripped)
                if len(self._log) > 200:
                    self._log = self._log[-100:]
            self._refresh()

        process.wait()
        success = process.returncode == 0

        if success:
            self.progress.update(task, completed=1)
            self._log.append(f"[green]✓ {label} done[/]")
        else:
            self.progress.update(task, description=f"[red]{label} failed[/]", completed=1)
            self._log.append(f"[red]✗ {label} failed (exit {process.returncode})[/]")

        self._refresh()

        if not _IS_TTY:
            if success:
                ok(f"{label} done")
            else:
                warn(f"{label} failed (exit {process.returncode})")

        return success
