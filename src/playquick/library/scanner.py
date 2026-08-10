from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from playquick.library.metadata import read_metadata
from playquick.models import ScanResult
from playquick.storage.database import Database

AUDIO_EXTENSIONS = {
    ".aac",
    ".aiff",
    ".alac",
    ".ape",
    ".flac",
    ".m4a",
    ".mp3",
    ".ogg",
    ".opus",
    ".wav",
    ".wma",
}


def audio_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        supported = path.suffix.lower() in AUDIO_EXTENSIONS
        if path.is_file() and not path.name.startswith(".") and supported:
            yield path.resolve()


class LibraryScanner:
    def __init__(self, database: Database) -> None:
        self.database = database

    def scan(self, roots: Iterable[Path]) -> ScanResult:
        added = updated = missing = 0
        errors: list[str] = []
        for raw_root in roots:
            root = raw_root.expanduser().resolve()
            if not root.is_dir():
                errors.append(f"Not a directory: {root}")
                continue
            with self.database.transaction() as connection:
                connection.execute(
                    "INSERT OR IGNORE INTO scan_roots(path) VALUES (?)", (str(root),)
                )
                known_rows = connection.execute("SELECT path FROM tracks").fetchall()
                known_under_root = {
                    Path(str(row["path"]))
                    for row in known_rows
                    if Path(str(row["path"])).is_relative_to(root)
                }
                seen: set[Path] = set()
                for path in audio_files(root):
                    seen.add(path)
                    stat = path.stat()
                    row = connection.execute(
                        "SELECT id, file_size, modified_ns, missing FROM tracks WHERE path = ?",
                        (str(path),),
                    ).fetchone()
                    if (
                        row
                        and int(row["file_size"]) == stat.st_size
                        and int(row["modified_ns"]) == stat.st_mtime_ns
                        and not bool(row["missing"])
                    ):
                        continue
                    metadata = read_metadata(path)
                    if metadata.error:
                        errors.append(f"{path}: {metadata.error}")
                    connection.execute(
                        """INSERT INTO tracks(
                               path, title, artist, album, genre, duration,
                               file_size, modified_ns, missing, scan_error
                           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                           ON CONFLICT(path) DO UPDATE SET
                               title=excluded.title, artist=excluded.artist,
                               album=excluded.album, genre=excluded.genre,
                               duration=excluded.duration, file_size=excluded.file_size,
                               modified_ns=excluded.modified_ns, missing=0,
                               scan_error=excluded.scan_error, updated_at=CURRENT_TIMESTAMP""",
                        (
                            str(path),
                            metadata.title,
                            metadata.artist,
                            metadata.album,
                            metadata.genre,
                            metadata.duration,
                            stat.st_size,
                            stat.st_mtime_ns,
                            metadata.error,
                        ),
                    )
                    if row:
                        updated += 1
                    else:
                        added += 1
                removed = known_under_root - seen
                if removed:
                    connection.executemany(
                        "UPDATE tracks SET missing = 1, updated_at = CURRENT_TIMESTAMP "
                        "WHERE path = ?",
                        ((str(path),) for path in removed),
                    )
                    missing += len(removed)
        return ScanResult(added, updated, missing, tuple(errors))
