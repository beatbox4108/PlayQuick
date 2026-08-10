from pathlib import Path

import pytest
from textual.widgets import DataTable

from playquick.models import LibraryGroupKind
from playquick.storage import Database
from playquick.tui.app import PlayQuickApp
from playquick.tui.widgets import table_text


def test_table_text_truncates_by_terminal_cell_width() -> None:
    text = table_text("長いタイトル" * 10, 20)

    assert text.cell_len == 20
    assert text.plain.endswith("…")


@pytest.mark.asyncio
async def test_tui_starts_without_mpv(tmp_path: Path) -> None:
    app = PlayQuickApp(
        database_path=tmp_path / "library.db",
        config_path=tmp_path / "config.toml",
        setup_prompt=False,
    )
    async with app.run_test(size=(100, 35)) as pilot:
        assert app.query_one("#library")
        await pilot.press("ctrl+f")
        assert app.query_one("#search").has_class("visible")


@pytest.mark.asyncio
async def test_tui_drills_into_album_and_returns(tmp_path: Path) -> None:
    database_path = tmp_path / "library.db"
    database = Database(database_path)
    database.migrate()
    with database.transaction() as connection:
        connection.execute(
            """INSERT INTO tracks(
                   path, title, artist, album, genre, duration, file_size, modified_ns
               ) VALUES ('song.mp3', 'Song', 'Artist', 'Album', 'Rock', 60, 1, 1)"""
        )
    app = PlayQuickApp(
        database_path=database_path,
        config_path=tmp_path / "config.toml",
        setup_prompt=False,
    )
    async with app.run_test(size=(100, 35)):
        app.show_groups(LibraryGroupKind.ALBUM)
        table = app.query_one("#library", DataTable)
        assert table.row_count == 1

        await app.play_selected()
        assert app._drilldown_kind == LibraryGroupKind.ALBUM
        assert app.selected_track() is not None

        app.action_browser_back()
        assert app._group_kind == LibraryGroupKind.ALBUM
