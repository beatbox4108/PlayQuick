from typing import ClassVar

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Label


class PlayQuickApp(App[None]):
    """Temporary shell replaced by the full player screen in later commits."""

    TITLE = "PlayQuick"
    BINDINGS: ClassVar = [("ctrl+q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("PlayQuick is starting…")
        yield Footer()
