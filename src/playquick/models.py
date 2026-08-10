from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class PlaybackStatus(StrEnum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"
    ERROR = "error"


class RepeatMode(StrEnum):
    OFF = "off"
    ONE = "one"
    ALL = "all"


@dataclass(slots=True, frozen=True)
class Track:
    id: int
    path: Path
    title: str
    artist: str = "Unknown Artist"
    album: str = "Unknown Album"
    genre: str = ""
    duration: float = 0.0
    missing: bool = False


@dataclass(slots=True)
class PlaybackState:
    status: PlaybackStatus = PlaybackStatus.STOPPED
    track: Track | None = None
    position: float = 0.0
    duration: float = 0.0
    volume: int = 70
    shuffle: bool = False
    repeat: RepeatMode = RepeatMode.OFF
    error: str | None = None


@dataclass(slots=True, frozen=True)
class QueueItem:
    id: int
    track: Track
    position: int
    play_next: bool = False


@dataclass(slots=True, frozen=True)
class ScanResult:
    added: int = 0
    updated: int = 0
    missing: int = 0
    errors: tuple[str, ...] = field(default_factory=tuple)

