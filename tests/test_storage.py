from pathlib import Path

from playquick.config import AppConfig, ConfigStore
from playquick.storage import Database, LibraryRepository


def test_config_roundtrip(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "config.toml")
    expected = AppConfig(music_dirs=["/music"], volume=55)
    store.save(expected)
    assert store.load() == expected


def test_database_migrates_and_saves_state(tmp_path: Path) -> None:
    database = Database(tmp_path / "library.db")
    database.migrate()
    repository = LibraryRepository(database)
    repository.save_state("volume", "42")
    assert repository.load_state("volume") == "42"

