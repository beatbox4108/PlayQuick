from __future__ import annotations

from rich.text import Text
from textual import events
from textual.message import Message
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


def seek_position(pointer_x: int, width: int, duration: float) -> float:
    if width <= 1 or duration <= 0:
        return 0
    ratio = max(0.0, min(1.0, pointer_x / (width - 1)))
    return ratio * duration


def _time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class PlayerBar(Widget):
    class SeekRequested(Message):
        def __init__(self, position: float) -> None:
            super().__init__()
            self.position = position

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
        time_and_volume = (
            f"  {_time(state.position)} / {_time(state.duration)}  VOL {state.volume}%"
        )
        details_width = max(8, self.content_size.width - len(time_and_volume) - 11)
        result = Text()
        result.append(" LOCAL ", style="black on green bold")
        result.append(f" {icon} ", style="green bold")
        result.append_text(table_text(f"{title}{artist}", details_width))
        result.append(time_and_volume, style="cyan")
        if state.error:
            result.append(f"   {state.error}", style="red")
        result.append("\n")
        bar_width = max(1, self.content_size.width)
        if state.duration > 0 and state.track:
            ratio = max(0.0, min(1.0, state.position / state.duration))
            marker = min(bar_width - 1, round(ratio * (bar_width - 1)))
            result.append("━" * marker, style="green")
            result.append("●", style="green bold")
            result.append("─" * (bar_width - marker - 1), style="dim")
        else:
            result.append("─" * bar_width, style="dim")
        return result

    def on_click(self, event: events.Click) -> None:
        state = self.state
        region = self.content_region
        if (
            not state.track
            or state.duration <= 0
            or event.screen_y != region.y + 1
            or not (region.x <= event.screen_x < region.right)
        ):
            return
        position = seek_position(event.screen_x - region.x, region.width, state.duration)
        self.post_message(self.SeekRequested(position))
        event.stop()
