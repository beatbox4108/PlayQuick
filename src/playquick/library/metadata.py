from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mutagen


@dataclass(slots=True, frozen=True)
class AudioMetadata:
    title: str
    artist: str
    album: str
    genre: str
    duration: float
    error: str | None = None


def _first(tags: Any, keys: tuple[str, ...], default: str) -> str:
    if tags is None:
        return default
    for key in keys:
        value = tags.get(key)
        if isinstance(value, list) and value:
            return str(value[0])
        if value:
            return str(value)
    return default


def read_metadata(path: Path) -> AudioMetadata:
    try:
        audio = mutagen.File(path, easy=True)
        if audio is None:
            return AudioMetadata(path.stem, "Unknown Artist", "Unknown Album", "", 0.0)
        tags = audio.tags
        info = getattr(audio, "info", None)
        duration = float(getattr(info, "length", 0.0))
        return AudioMetadata(
            title=_first(tags, ("title",), path.stem),
            artist=_first(tags, ("artist", "albumartist"), "Unknown Artist"),
            album=_first(tags, ("album",), "Unknown Album"),
            genre=_first(tags, ("genre",), ""),
            duration=duration,
        )
    except Exception as error:  # Mutagen raises format-specific exceptions.
        return AudioMetadata(
            path.stem,
            "Unknown Artist",
            "Unknown Album",
            "",
            0.0,
            f"{type(error).__name__}: {error}",
        )

