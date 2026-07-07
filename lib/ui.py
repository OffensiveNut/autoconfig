"""
Shared UI utilities for all Layer 2 scripts.

Provides consistent colored output and a progress bar runner via `rich`.
Import in any script:

    from lib.ui import console, info, warn, ok, StepRunner, run
"""

import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

console = Console()


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
    """Run a sequence of steps with a unified progress bar.

    Usage:
        with StepRunner() as steps:
            steps.run("Label", some_function)
            steps.run("Another", another_function)
    """

    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
        )

    def __enter__(self):
        self.progress.__enter__()
        return self

    def __exit__(self, *args):
        self.progress.__exit__(*args)

    def run(self, label: str, fn, *args, **kwargs):
        task = self.progress.add_task(f"[cyan]{label}...", total=1)
        try:
            fn(*args, **kwargs)
        except Exception as e:
            self.progress.update(task, description=f"[red]{label} failed[/]", completed=1)
            warn(f"{label}: {e}")
            return False
        self.progress.update(task, completed=1)
        return True
