from pathlib import Path

from playquick.library import LibraryScanner, ScanPhase, ScanProgress
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


def test_scanner_reports_discovery_and_file_progress(tmp_path: Path) -> None:
    music = tmp_path / "Music"
    music.mkdir()
    (music / "one.mp3").write_bytes(b"one")
    (music / "two.flac").write_bytes(b"two")
    database = Database(tmp_path / "library.db")
    database.migrate()
    events: list[ScanProgress] = []

    LibraryScanner(database).scan([music], progress=events.append)

    assert events[0].phase == ScanPhase.DISCOVERING
    scanning = [event for event in events if event.phase == ScanPhase.SCANNING]
    assert scanning[-1].processed == 2
    assert scanning[-1].total == 2
    assert events[-1].phase == ScanPhase.COMPLETE
