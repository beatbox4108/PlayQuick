from __future__ import annotations

import asyncio
from typing import Any

import httpx

from playquick.spotify.auth import SpotifyAuth
from playquick.spotify.models import (
    SpotifyContainer,
    SpotifyDevice,
    SpotifyPlayback,
    SpotifyTrack,
)

API_URL = "https://api.spotify.com/v1"


class SpotifyError(RuntimeError):
    def __init__(self, status: int, message: str, reason: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.reason = reason


class SpotifyClient:
    def __init__(self, auth: SpotifyAuth, client: httpx.AsyncClient | None = None) -> None:
        self.auth = auth
        self.client = client or httpx.AsyncClient(base_url=API_URL, timeout=30)

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        for attempt in range(2):
            token = await self.auth.token()
            response = await self.client.request(
                method, path, headers={"Authorization": f"Bearer {token}"}, **kwargs
            )
            if response.status_code == 429 and attempt == 0:
                await asyncio.sleep(min(float(response.headers.get("Retry-After", "1")), 60))
                continue
            if response.status_code >= 400:
                try:
                    error = response.json().get("error", {})
                    message = str(error.get("message", response.text))
                    reason = error.get("reason")
                except ValueError:
                    message, reason = response.text, None
                raise SpotifyError(response.status_code, message, reason)
            if response.status_code == 204 or not response.content:
                return None
            return response.json()
        raise SpotifyError(429, "Spotify API quota exceeded", "QUOTA_EXCEEDED")

    async def devices(self) -> list[SpotifyDevice]:
        value = await self.request("GET", "/me/player/devices")
        return [SpotifyDevice.from_mapping(item) for item in value.get("devices", [])]

    async def playback(self) -> SpotifyPlayback | None:
        value = await self.request("GET", "/me/player")
        return SpotifyPlayback.from_mapping(value) if value else None

    async def transfer(self, device_id: str, *, play: bool = False) -> None:
        await self.request("PUT", "/me/player", json={"device_ids": [device_id], "play": play})

    async def play(self, *, uri: str | None = None, context_uri: str | None = None) -> None:
        body: dict[str, object] = {}
        if uri:
            body["uris"] = [uri]
        if context_uri:
            body["context_uri"] = context_uri
        await self.request("PUT", "/me/player/play", json=body)

    async def pause(self) -> None:
        await self.request("PUT", "/me/player/pause")

    async def next(self) -> None:
        await self.request("POST", "/me/player/next")

    async def previous(self) -> None:
        await self.request("POST", "/me/player/previous")

    async def seek(self, position_ms: int) -> None:
        await self.request("PUT", "/me/player/seek", params={"position_ms": position_ms})

    async def volume(self, percent: int) -> None:
        await self.request(
            "PUT", "/me/player/volume", params={"volume_percent": max(0, min(100, percent))}
        )

    async def shuffle(self, enabled: bool) -> None:
        await self.request("PUT", "/me/player/shuffle", params={"state": str(enabled).lower()})

    async def repeat(self, mode: str) -> None:
        await self.request("PUT", "/me/player/repeat", params={"state": mode})

    async def queue(self) -> list[SpotifyTrack]:
        value = await self.request("GET", "/me/player/queue")
        return [SpotifyTrack.from_mapping(item) for item in value.get("queue", [])]

    async def add_to_queue(self, uri: str) -> None:
        await self.request("POST", "/me/player/queue", params={"uri": uri})

    async def search(self, query: str, *, offset: int = 0) -> list[SpotifyTrack]:
        value = await self.request(
            "GET", "/search", params={"q": query, "type": "track", "limit": 10, "offset": offset}
        )
        return [
            SpotifyTrack.from_mapping(item)
            for item in value.get("tracks", {}).get("items", [])
        ]

    async def saved_tracks(self, *, offset: int = 0) -> list[SpotifyTrack]:
        value = await self.request("GET", "/me/tracks", params={"limit": 10, "offset": offset})
        return [
            SpotifyTrack.from_mapping(item.get("track", {})) for item in value.get("items", [])
        ]

    async def recent(self) -> list[SpotifyTrack]:
        value = await self.request("GET", "/me/player/recently-played", params={"limit": 10})
        return [
            SpotifyTrack.from_mapping(item.get("track", {})) for item in value.get("items", [])
        ]

    async def top_tracks(self) -> list[SpotifyTrack]:
        value = await self.request("GET", "/me/top/tracks", params={"limit": 10})
        return [SpotifyTrack.from_mapping(item) for item in value.get("items", [])]

    async def saved_albums(self, *, offset: int = 0) -> list[SpotifyContainer]:
        value = await self.request("GET", "/me/albums", params={"limit": 10, "offset": offset})
        return [
            SpotifyContainer.from_mapping(item.get("album", {}), "album")
            for item in value.get("items", [])
        ]

    async def playlists(self, *, offset: int = 0) -> list[SpotifyContainer]:
        value = await self.request(
            "GET", "/me/playlists", params={"limit": 10, "offset": offset}
        )
        return [SpotifyContainer.from_mapping(item, "playlist") for item in value.get("items", [])]

    async def album_tracks(self, album_id: str, *, offset: int = 0) -> list[SpotifyTrack]:
        value = await self.request(
            "GET", f"/albums/{album_id}/tracks", params={"limit": 10, "offset": offset}
        )
        return [SpotifyTrack.from_mapping(item) for item in value.get("items", [])]

    async def artist_albums(self, artist_id: str, *, offset: int = 0) -> list[SpotifyContainer]:
        value = await self.request(
            "GET", f"/artists/{artist_id}/albums", params={"limit": 10, "offset": offset}
        )
        return [SpotifyContainer.from_mapping(item, "album") for item in value.get("items", [])]

    async def playlist_tracks(self, playlist_id: str, *, offset: int = 0) -> list[SpotifyTrack]:
        value = await self.request(
            "GET", f"/playlists/{playlist_id}/items", params={"limit": 10, "offset": offset}
        )
        tracks = []
        for wrapper in value.get("items", []):
            item = wrapper.get("item")
            if isinstance(item, dict) and item.get("type", "track") == "track":
                tracks.append(SpotifyTrack.from_mapping(item))
        return tracks
