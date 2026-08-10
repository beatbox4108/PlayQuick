from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path

from playquick.models import QueueItem, Track
from playquick.storage.database import Database


def _track(row: sqlite3.Row) -> Track:
    return Track(
        id=int(row["id"]),
        path=Path(str(row["path"])),
        title=str(row["title"]),
        artist=str(row["artist"]),
        album=str(row["album"]),
        genre=str(row["genre"]),
        duration=float(row["duration"]),
        missing=bool(row["missing"]),
    )


class LibraryRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def tracks(self, *, limit: int = 500, offset: int = 0) -> list[Track]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM tracks WHERE missing = 0 "
                "ORDER BY title COLLATE NOCASE LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [_track(row) for row in rows]

    def search(self, query: str, *, limit: int = 100) -> list[Track]:
        pattern = f"%{query}%"
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT * FROM tracks WHERE missing = 0 AND
                   (title LIKE ? OR artist LIKE ? OR album LIKE ? OR genre LIKE ?)
                   ORDER BY title COLLATE NOCASE LIMIT ?""",
                (pattern, pattern, pattern, pattern, limit),
            ).fetchall()
        return [_track(row) for row in rows]

    def set_favorite(self, track_id: int, favorite: bool) -> None:
        with self.database.transaction() as connection:
            if favorite:
                connection.execute(
                    "INSERT OR IGNORE INTO favorites(track_id) VALUES (?)", (track_id,)
                )
            else:
                connection.execute("DELETE FROM favorites WHERE track_id = ?", (track_id,))

    def favorites(self) -> list[Track]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT tracks.* FROM tracks JOIN favorites ON tracks.id = favorites.track_id
                   WHERE tracks.missing = 0 ORDER BY favorites.created_at DESC"""
            ).fetchall()
        return [_track(row) for row in rows]

    def add_history(self, track_id: int) -> None:
        with self.database.transaction() as connection:
            connection.execute("INSERT INTO play_history(track_id) VALUES (?)", (track_id,))

    def history(self, limit: int = 100) -> list[Track]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT tracks.* FROM play_history
                   JOIN tracks ON tracks.id = play_history.track_id
                   ORDER BY play_history.played_at DESC, play_history.id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [_track(row) for row in rows]

    def replace_queue(self, track_ids: Sequence[int]) -> None:
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM queue_items")
            connection.executemany(
                "INSERT INTO queue_items(track_id, position) VALUES (?, ?)",
                ((track_id, index) for index, track_id in enumerate(track_ids)),
            )

    def queue(self) -> list[QueueItem]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT queue_items.id queue_id, queue_items.position, queue_items.play_next,
                          tracks.* FROM queue_items JOIN tracks ON tracks.id = queue_items.track_id
                   ORDER BY queue_items.play_next DESC, queue_items.position"""
            ).fetchall()
        return [
            QueueItem(
                id=int(row["queue_id"]),
                track=_track(row),
                position=int(row["position"]),
                play_next=bool(row["play_next"]),
            )
            for row in rows
        ]

    def save_state(self, key: str, value: str) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO app_state(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def load_state(self, key: str) -> str | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT value FROM app_state WHERE key = ?", (key,)).fetchone()
        return str(row["value"]) if row else None
