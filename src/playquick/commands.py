from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from playquick.config import default_database_path
from playquick.library import LibraryScanner
from playquick.storage import Database


def scan_paths(paths: Sequence[str]) -> int:
    database = Database(default_database_path())
    database.migrate()
    result = LibraryScanner(database).scan(Path(path) for path in paths)
    print(f"Added {result.added}, updated {result.updated}, missing {result.missing}")
    for error in result.errors:
        print(f"Warning: {error}")
    return 0 if not result.errors else 2

