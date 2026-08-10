from __future__ import annotations

from pathlib import Path

from playquick.models import Track
from playquick.playback.queue import PlaybackQueue
from playquick.storage import Database, LibraryRepository


def seed_tracks(database: Database) -> list[Track]:
    with database.transaction() as connection:
        for index in range(3):
            connection.execute(
                """INSERT INTO tracks(
                       path, title, file_size, modified_ns
                   ) VALUES (?, ?, 1, 1)""",
                (str(Path(f"{index}.mp3")), f"Track {index}"),
            )
    return LibraryRepository(database).tracks()


def test_explicit_queue_precedes_context_and_undoes(tmp_path: Path) -> None:
    database = Database(tmp_path / "library.db")
    database.migrate()
    repository = LibraryRepository(database)
    tracks = seed_tracks(database)
    queue = PlaybackQueue(repository)
    queue.set_context([tracks[1]])
    queue.append(tracks[2])

    assert queue.pop_next() == tracks[2]
    assert queue.pop_next() == tracks[1]
    queue.append(tracks[2])
    queue.remove(0)
    assert queue.undo()
    assert queue.items()[0] == tracks[2]


def test_play_next_is_first(tmp_path: Path) -> None:
    database = Database(tmp_path / "library.db")
    database.migrate()
    repository = LibraryRepository(database)
    tracks = seed_tracks(database)
    queue = PlaybackQueue(repository)
    queue.append(tracks[0])
    queue.play_next(tracks[1])
    assert queue.pop_next() == tracks[1]
