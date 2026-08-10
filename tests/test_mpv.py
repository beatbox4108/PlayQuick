from __future__ import annotations

import json
from pathlib import Path

import pytest

from playquick.models import PlaybackStatus, Track
from playquick.playback.mpv import MpvController


class FakeTransport:
    def __init__(self) -> None:
        self.commands: list[list[object]] = []
        self.responses: list[bytes] = []

    async def connect(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def send_line(self, data: bytes) -> None:
        request = json.loads(data)
        self.commands.append(request["command"])
        self.responses.append(
            json.dumps({"request_id": request["request_id"], "error": "success"}).encode()
        )

    async def read_line(self) -> bytes:
        return self.responses.pop(0)


class EndedTrackTransport(FakeTransport):
    async def send_line(self, data: bytes) -> None:
        request = json.loads(data)
        command = request["command"]
        self.commands.append(command)
        error = (
            "property unavailable"
            if command[:2] == ["get_property", "time-pos"]
            else "success"
        )
        self.responses.append(
            json.dumps({"request_id": request["request_id"], "error": error}).encode()
        )


@pytest.mark.asyncio
async def test_mpv_controller_loads_and_pauses_track() -> None:
    transport = FakeTransport()
    controller = MpvController(Path("mpv"), transport)
    await controller.start()
    track = Track(1, Path("song.mp3"), "Song")
    await controller.play(track)
    await controller.pause(True)

    assert ["loadfile", "song.mp3", "replace"] in transport.commands
    assert controller.state.status == PlaybackStatus.PAUSED


@pytest.mark.asyncio
async def test_poll_accepts_properties_disappearing_after_eof() -> None:
    controller = MpvController(Path("mpv"), EndedTrackTransport())
    await controller.start()
    await controller.play(Track(1, Path("short.wav"), "Short", duration=1.0))

    state = await controller.poll()

    assert state.position == 0
    assert state.duration == 1.0
    assert state.status == PlaybackStatus.STOPPED
