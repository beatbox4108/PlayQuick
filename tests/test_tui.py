from pathlib import Path

import pytest

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
