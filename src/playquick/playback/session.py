from __future__ import annotations

from collections.abc import Sequence

from playquick.models import PlaybackStatus, Track
from playquick.playback.base import PlaybackController
from playquick.playback.queue import PlaybackQueue
from playquick.storage.repository import LibraryRepository


class PlaybackSession:
    def __init__(
        self,
        controller: PlaybackController,
        repository: LibraryRepository,
        queue: PlaybackQueue,
    ) -> None:
        self.controller = controller
        self.repository = repository
        self.queue = queue

    async def play_from(self, tracks: Sequence[Track], index: int) -> None:
        track = tracks[index]
        self.queue.set_context(tracks[index + 1 :])
        await self.play(track)

    async def play(self, track: Track) -> None:
        await self.controller.play(track)
        self.repository.add_history(track.id)

    async def next(self) -> Track | None:
        track = self.queue.pop_next()
        if track:
            await self.play(track)
        else:
            await self.controller.stop()
        return track

    async def toggle_pause(self) -> None:
        paused = self.controller.state.status == PlaybackStatus.PLAYING
        await self.controller.pause(paused)

    async def close(self) -> None:
        state = self.controller.state
        self.repository.save_state("volume", str(state.volume))
        self.repository.save_state("position", str(state.position))
        if state.track:
            self.repository.save_state("track_id", str(state.track.id))
        await self.controller.stop()
        await self.controller.close()

