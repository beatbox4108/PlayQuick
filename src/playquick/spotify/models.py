from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class SpotifyImage:
    url: str
    width: int | None = None
    height: int | None = None


@dataclass(slots=True, frozen=True)
class SpotifyTrack:
    uri: str
    name: str
    artist: str
    album: str
    duration_ms: int
    external_url: str | None = None

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> SpotifyTrack:
        artists = value.get("artists") or []
        artist = ", ".join(str(item.get("name", "")) for item in artists) or "Unknown Artist"
        album = value.get("album") or {}
        return cls(
            uri=str(value.get("uri", "")),
            name=str(value.get("name", "Unknown Track")),
            artist=artist,
            album=str(album.get("name", "Unknown Album")),
            duration_ms=int(value.get("duration_ms") or 0),
            external_url=(value.get("external_urls") or {}).get("spotify"),
        )


@dataclass(slots=True, frozen=True)
class SpotifyDevice:
    id: str
    name: str
    type: str
    volume_percent: int | None
    active: bool

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> SpotifyDevice:
        return cls(
            id=str(value.get("id", "")),
            name=str(value.get("name", "Unknown device")),
            type=str(value.get("type", "Unknown")),
            volume_percent=value.get("volume_percent"),
            active=bool(value.get("is_active", False)),
        )


@dataclass(slots=True, frozen=True)
class SpotifyContainer:
    uri: str
    name: str
    kind: str
    owner: str | None = None
    external_url: str | None = None

    @classmethod
    def from_mapping(cls, value: dict[str, Any], kind: str) -> SpotifyContainer:
        owner = value.get("owner") or {}
        return cls(
            uri=str(value.get("uri", "")),
            name=str(value.get("name", "Unknown")),
            kind=kind,
            owner=owner.get("display_name") or owner.get("id"),
            external_url=(value.get("external_urls") or {}).get("spotify"),
        )


@dataclass(slots=True, frozen=True)
class SpotifyPlayback:
    playing: bool
    progress_ms: int
    track: SpotifyTrack | None
    device: SpotifyDevice | None
    shuffle: bool = False
    repeat: str = "off"

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> SpotifyPlayback:
        item = value.get("item")
        device = value.get("device")
        return cls(
            playing=bool(value.get("is_playing", False)),
            progress_ms=int(value.get("progress_ms") or 0),
            track=SpotifyTrack.from_mapping(item) if isinstance(item, dict) else None,
            device=SpotifyDevice.from_mapping(device) if isinstance(device, dict) else None,
            shuffle=bool(value.get("shuffle_state", False)),
            repeat=str(value.get("repeat_state", "off")),
        )
