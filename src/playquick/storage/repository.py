from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path

from playquick.models import LibraryGroup, LibraryGroupKind, QueueItem, Track
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

    def tracks(self, *, limit: int = 500, offset: int = 0, order_by: str = "title") -> list[Track]:
        order = {
            "title": "title COLLATE NOCASE",
            "artist": "artist COLLATE NOCASE, album COLLATE NOCASE, title COLLATE NOCASE",
            "album": "album COLLATE NOCASE, title COLLATE NOCASE",
            "genre": "genre COLLATE NOCASE, artist COLLATE NOCASE, title COLLATE NOCASE",
            "path": "path COLLATE NOCASE",
        }.get(order_by, "title COLLATE NOCASE")
        with self.database.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM tracks WHERE missing = 0 ORDER BY {order} LIMIT ? OFFSET ?",
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

    def groups(self, kind: LibraryGroupKind) -> list[LibraryGroup]:
        selections = {
            LibraryGroupKind.ALBUM: (
                "album",
                "CASE WHEN COUNT(DISTINCT artist) = 1 THEN MIN(artist) ELSE 'Various Artists' END",
            ),
            LibraryGroupKind.ARTIST: (
                "artist",
                "CAST(COUNT(DISTINCT album) AS TEXT) || "
                "CASE WHEN COUNT(DISTINCT album) = 1 THEN ' album' ELSE ' albums' END",
            ),
            LibraryGroupKind.GENRE: (
                "genre",
                "CAST(COUNT(DISTINCT artist) AS TEXT) || "
                "CASE WHEN COUNT(DISTINCT artist) = 1 THEN ' artist' ELSE ' artists' END",
            ),
        }
        column, detail = selections[kind]
        with self.database.connect() as connection:
            rows = connection.execute(
                f"""SELECT {column} value, {detail} detail,
                           COUNT(*) track_count, COALESCE(SUM(duration), 0) duration
                    FROM tracks WHERE missing = 0
                    GROUP BY {column} ORDER BY {column} COLLATE NOCASE"""
            ).fetchall()
        return [
            LibraryGroup(
                kind=kind,
                value=str(row["value"]),
                name=str(row["value"]) or "Unknown Genre",
                detail=str(row["detail"]),
                track_count=int(row["track_count"]),
                duration=float(row["duration"]),
            )
            for row in rows
        ]

    def tracks_for_group(self, kind: LibraryGroupKind, value: str) -> list[Track]:
        column = {
            LibraryGroupKind.ALBUM: "album",
            LibraryGroupKind.ARTIST: "artist",
            LibraryGroupKind.GENRE: "genre",
        }[kind]
        with self.database.connect() as connection:
            rows = connection.execute(
                f"""SELECT * FROM tracks
                    WHERE missing = 0 AND {column} = ?
                    ORDER BY album COLLATE NOCASE, title COLLATE NOCASE""",
                (value,),
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

    def playlist_names(self) -> list[str]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT name FROM playlists ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return [str(row["name"]) for row in rows]

    def add_to_playlist(self, name: str, track_id: int) -> None:
        with self.database.transaction() as connection:
            connection.execute("INSERT OR IGNORE INTO playlists(name) VALUES (?)", (name,))
            playlist = connection.execute(
                "SELECT id FROM playlists WHERE name = ?", (name,)
            ).fetchone()
            assert playlist is not None
            position_row = connection.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 next FROM playlist_items "
                "WHERE playlist_id = ?",
                (int(playlist["id"]),),
            ).fetchone()
            position = int(position_row["next"]) if position_row else 0
            connection.execute(
                "INSERT INTO playlist_items(playlist_id, track_id, position) VALUES (?, ?, ?)",
                (int(playlist["id"]), track_id, position),
            )

    def playlist_tracks(self, name: str) -> list[Track]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT tracks.* FROM playlist_items
                   JOIN playlists ON playlists.id = playlist_items.playlist_id
                   JOIN tracks ON tracks.id = playlist_items.track_id
                   WHERE playlists.name = ? AND tracks.missing = 0
                   ORDER BY playlist_items.position""",
                (name,),
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
