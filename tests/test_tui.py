from pathlib import Path

import pytest

from playquick.tui.app import PlayQuickApp


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
