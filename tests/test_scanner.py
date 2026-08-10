from pathlib import Path

from playquick.library import LibraryScanner
from playquick.storage import Database, LibraryRepository


def test_scanner_indexes_and_marks_missing_files(tmp_path: Path) -> None:
    music = tmp_path / "Music"
    music.mkdir()
    track = music / "Artist - Song.mp3"
    track.write_bytes(b"not really mp3")
    database = Database(tmp_path / "library.db")
    database.migrate()
    scanner = LibraryScanner(database)

    first = scanner.scan([music])
    assert first.added == 1
    assert LibraryRepository(database).tracks()[0].title == "Artist - Song"

    track.unlink()
    second = scanner.scan([music])
    assert second.missing == 1
    assert LibraryRepository(database).tracks() == []


def test_scanner_reports_invalid_root(tmp_path: Path) -> None:
    database = Database(tmp_path / "library.db")
    database.migrate()
    result = LibraryScanner(database).scan([tmp_path / "missing"])
    assert result.errors

