from __future__ import annotations

from collections.abc import AsyncIterator

from playquick.spotify.client import SpotifyClient
from playquick.spotify.models import SpotifyContainer, SpotifyDevice, SpotifyPlayback, SpotifyTrack


class SpotifyRemoteController:
    """Remote-only controller; it never receives or decodes Spotify audio."""

    def __init__(self, client: SpotifyClient) -> None:
        self.client = client
        self.state: SpotifyPlayback | None = None

    async def devices(self) -> list[SpotifyDevice]:
        return await self.client.devices()

    async def transfer(self, device_id: str, *, play: bool = False) -> None:
        await self.client.transfer(device_id, play=play)

    async def play(self, track: SpotifyTrack) -> None:
        await self.client.play(uri=track.uri)

    async def pause(self) -> None:
        await self.client.pause()

    async def add_to_queue(self, track: SpotifyTrack) -> None:
        await self.client.add_to_queue(track.uri)

    async def search(self, query: str, *, offset: int = 0) -> list[SpotifyTrack]:
        return await self.client.search(query, offset=offset)

    async def saved_tracks(self, *, offset: int = 0) -> list[SpotifyTrack]:
        return await self.client.saved_tracks(offset=offset)

    async def saved_albums(self, *, offset: int = 0) -> list[SpotifyContainer]:
        return await self.client.saved_albums(offset=offset)

    async def playlists(self, *, offset: int = 0) -> list[SpotifyContainer]:
        return await self.client.playlists(offset=offset)

    async def album_tracks(self, album_id: str, *, offset: int = 0) -> list[SpotifyTrack]:
        return await self.client.album_tracks(album_id, offset=offset)

    async def playlist_tracks(
        self, playlist_id: str, *, offset: int = 0
    ) -> list[SpotifyTrack]:
        return await self.client.playlist_tracks(playlist_id, offset=offset)

    async def artist_albums(
        self, artist_id: str, *, offset: int = 0
    ) -> list[SpotifyContainer]:
        return await self.client.artist_albums(artist_id, offset=offset)

    async def recent(self) -> list[SpotifyTrack]:
        return await self.client.recent()

    async def top_tracks(self) -> list[SpotifyTrack]:
        return await self.client.top_tracks()

    async def poll(self) -> SpotifyPlayback | None:
        self.state = await self.client.playback()
        return self.state

    async def states(self) -> AsyncIterator[SpotifyPlayback | None]:
        while True:
            state = await self.poll()
            yield state
            interval = 3 if state and state.playing else 12
            import asyncio

            await asyncio.sleep(interval)

    async def close(self) -> None:
        await self.client.client.aclose()
        await self.client.auth.client.aclose()
