from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

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


async def install_mpv(manager: MpvRuntimeManager, callback: Callable[[Path], None]) -> None:
    executable = await asyncio.to_thread(manager.install)
    callback(executable)
