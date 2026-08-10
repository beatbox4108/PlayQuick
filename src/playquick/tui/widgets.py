from __future__ import annotations

from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

from playquick.models import PlaybackState, PlaybackStatus

TITLE_COLUMN_WIDTH = 48
ARTIST_COLUMN_WIDTH = 28
ALBUM_COLUMN_WIDTH = 32


def table_text(value: str, width: int) -> Text:
    """Return a single-line table cell capped by terminal display width."""
    text = Text(value, no_wrap=True, overflow="ellipsis")
    text.truncate(width, overflow="ellipsis")
    return text


def _time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class PlayerBar(Widget):
    state: reactive[PlaybackState] = reactive(PlaybackState, always_update=True)

    def render(self) -> Text:
        state = self.state
        icon = {
            PlaybackStatus.PLAYING: "▶",
            PlaybackStatus.PAUSED: "Ⅱ",
            PlaybackStatus.BUFFERING: "…",
            PlaybackStatus.ERROR: "!",
            PlaybackStatus.STOPPED: "■",
        }[state.status]
        title = state.track.title if state.track else "Nothing playing"
        artist = f" — {state.track.artist}" if state.track else ""
        result = Text()
        result.append(" LOCAL ", style="black on green bold")
        result.append(f" {icon} ", style="green bold")
        result.append(title, style="bold")
        result.append(artist, style="dim")
        result.append(
            f"   {_time(state.position)} / {_time(state.duration)}   VOL {state.volume}%",
            style="cyan",
        )
        if state.error:
            result.append(f"   {state.error}", style="red")
        return result
