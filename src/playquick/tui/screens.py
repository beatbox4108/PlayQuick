from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static, Switch

from playquick.config import AppConfig
from playquick.runtime.mpv_manager import MpvRuntimeManager


class HelpScreen(ModalScreen[None]):
    BINDINGS: ClassVar = [("escape", "dismiss", "Close"), ("?", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(
                """[b]PlayQuick keys[/b]

↑/↓ or j/k  Move                 Enter  Play/open
Space        Play/pause           A      Play next
a            Add to queue         Delete Remove queue item
←/→          Seek 5 seconds       Shift+←/→ Seek 30 seconds
n / b        Next / previous      /      Filter library
Ctrl+f       Global search        u      Undo queue edit
?            Help                 Ctrl+q Quit"""
            ),
            Button("Close", id="close", variant="primary"),
            id="help-dialog",
        )

    def on_button_pressed(self) -> None:
        self.dismiss()


class MpvSetupScreen(ModalScreen[bool]):
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("mpv was not found. Download the verified PlayQuick-managed runtime?"),
            Label("The runtime is stored in your user data directory; no administrator access."),
            Button("Download", id="download", variant="primary"),
            Button("Later", id="later"),
            id="mpv-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "download")


class SettingsScreen(ModalScreen[AppConfig | None]):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Settings"),
            Label("Music directories (separated by semicolons)"),
            Input(";".join(self.config.music_dirs), id="music-dirs"),
            Label("mpv executable override"),
            Input(self.config.mpv_path or "", id="mpv-path"),
            Label("Spotify Client ID (optional, experimental)"),
            Input(self.config.spotify_client_id or "", id="spotify-client-id"),
            Label("Enable Spotify library scopes"),
            Switch(self.config.spotify_extended_library, id="spotify-extended"),
            Select([("Dark", "dark"), ("Light", "light")], value=self.config.theme, id="theme"),
            Button("Save", id="save", variant="primary"),
            Button("Cancel", id="cancel"),
            id="settings-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "save":
            self.dismiss(None)
            return
        theme = self.query_one("#theme", Select).value
        self.dismiss(
            AppConfig(
                music_dirs=[
                    value.strip()
                    for value in self.query_one("#music-dirs", Input).value.split(";")
                    if value.strip()
                ],
                mpv_path=self.query_one("#mpv-path", Input).value.strip() or None,
                theme=str(theme),
                volume=self.config.volume,
                spotify_client_id=(
                    self.query_one("#spotify-client-id", Input).value.strip() or None
                ),
                spotify_extended_library=self.query_one("#spotify-extended", Switch).value,
                keybindings=self.config.keybindings,
            )
        )


async def install_mpv(manager: MpvRuntimeManager, callback: Callable[[Path], None]) -> None:
    executable = await asyncio.to_thread(manager.install)
    callback(executable)
