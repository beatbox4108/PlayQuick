from pathlib import Path

from playquick.storage import Database, LibraryRepository


def test_playlist_roundtrip(tmp_path: Path) -> None:
    database = Database(tmp_path / "library.db")
    database.migrate()
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO tracks(path, title, file_size, modified_ns) "
            "VALUES ('song.mp3', 'Song', 1, 1)"
        )
    repository = LibraryRepository(database)
    track = repository.tracks()[0]
    repository.add_to_playlist("Quick Picks", track.id)
    assert repository.playlist_names() == ["Quick Picks"]
    assert repository.playlist_tracks("Quick Picks") == [track]
