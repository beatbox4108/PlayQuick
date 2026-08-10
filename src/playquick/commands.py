from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from playquick.config import default_database_path
from playquick.library import LibraryScanner, ScanPhase, ScanProgress
from playquick.storage import Database


def scan_paths(paths: Sequence[str]) -> int:
    database = Database(default_database_path())
    database.migrate()
    console = Console()
    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as display:
        task = display.add_task("Discovering music files", total=None)

        def update(value: ScanProgress) -> None:
            if value.phase == ScanPhase.DISCOVERING:
                display.update(task, description=f"Discovering {value.root}", total=None)
                return
            description = (
                f"Scanning {value.root.name or value.root} "
                f"[green]+{value.added}[/] [yellow]~{value.updated}[/] "
                f"[dim]={value.skipped}[/] [red]!{value.errors}[/]"
            )
            display.update(
                task,
                description=description,
                completed=value.processed,
                total=value.total,
            )

        result = LibraryScanner(database).scan((Path(path) for path in paths), progress=update)
    console.print(f"Added {result.added}, updated {result.updated}, missing {result.missing}")
    for error in result.errors:
        console.print(f"[yellow]Warning:[/] {error}")
    return 0 if not result.errors else 2
