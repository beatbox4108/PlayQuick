from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA_VERSION = 1

MIGRATION_1 = """
CREATE TABLE IF NOT EXISTS schema_meta (
    version INTEGER NOT NULL
);
INSERT INTO schema_meta(version)
SELECT 0 WHERE NOT EXISTS (SELECT 1 FROM schema_meta);

CREATE TABLE scan_roots (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    enabled INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE tracks (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    artist TEXT NOT NULL DEFAULT 'Unknown Artist',
    album TEXT NOT NULL DEFAULT 'Unknown Album',
    genre TEXT NOT NULL DEFAULT '',
    duration REAL NOT NULL DEFAULT 0,
    file_size INTEGER NOT NULL,
    modified_ns INTEGER NOT NULL,
    missing INTEGER NOT NULL DEFAULT 0,
    scan_error TEXT,
    added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX tracks_title_idx ON tracks(title COLLATE NOCASE);
CREATE INDEX tracks_artist_idx ON tracks(artist COLLATE NOCASE);
CREATE INDEX tracks_album_idx ON tracks(album COLLATE NOCASE);

CREATE TABLE playlists (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE playlist_items (
    playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    track_id INTEGER NOT NULL REFERENCES tracks(id),
    position INTEGER NOT NULL,
    PRIMARY KEY (playlist_id, position)
);
CREATE TABLE favorites (
    track_id INTEGER PRIMARY KEY REFERENCES tracks(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE play_history (
    id INTEGER PRIMARY KEY,
    track_id INTEGER NOT NULL REFERENCES tracks(id),
    played_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE queue_items (
    id INTEGER PRIMARY KEY,
    track_id INTEGER NOT NULL REFERENCES tracks(id),
    position INTEGER NOT NULL UNIQUE,
    play_next INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE app_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
UPDATE schema_meta SET version = 1;
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def migrate(self) -> None:
        with self.connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_meta'"
            ).fetchone()
            version = 0
            if exists:
                row = connection.execute("SELECT version FROM schema_meta").fetchone()
                version = int(row["version"]) if row else 0
            if version < 1:
                connection.executescript(MIGRATION_1)
            row = connection.execute("SELECT version FROM schema_meta").fetchone()
            actual = int(row["version"]) if row else 0
            if actual != SCHEMA_VERSION:
                raise RuntimeError(f"Unsupported database schema version: {actual}")

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

