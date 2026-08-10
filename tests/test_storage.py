from pathlib import Path

from playquick.config import AppConfig, ConfigStore
from playquick.models import LibraryGroupKind
from playquick.storage import Database, LibraryRepository


def test_config_roundtrip(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "config.toml")
    expected = AppConfig(music_dirs=["/music"], volume=55, keybindings={"play": "space"})
    store.save(expected)
    assert store.load() == expected


def test_database_migrates_and_saves_state(tmp_path: Path) -> None:
    database = Database(tmp_path / "library.db")
    database.migrate()
    repository = LibraryRepository(database)
    repository.save_state("volume", "42")
    assert repository.load_state("volume") == "42"


def test_repository_browses_album_groups_and_tracks(tmp_path: Path) -> None:
    database = Database(tmp_path / "library.db")
    database.migrate()
    with database.transaction() as connection:
        connection.executemany(
            """INSERT INTO tracks(
                   path, title, artist, album, genre, duration, file_size, modified_ns
               ) VALUES (?, ?, ?, ?, ?, ?, 1, 1)""",
            [
                ("one.mp3", "One", "Artist", "Album", "Rock", 60),
                ("two.mp3", "Two", "Artist", "Album", "Rock", 120),
                ("three.mp3", "Three", "Other", "Second", "Jazz", 180),
            ],
        )
    repository = LibraryRepository(database)

    albums = repository.groups(LibraryGroupKind.ALBUM)
    album = next(group for group in albums if group.name == "Album")

    assert album.detail == "Artist"
    assert album.track_count == 2
    assert [track.title for track in repository.tracks_for_group(album.kind, album.value)] == [
        "One",
        "Two",
    ]
