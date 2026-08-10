from __future__ import annotations

import asyncio
import json
import os
import tempfile
import uuid
from collections.abc import AsyncIterator
from contextlib import suppress
from pathlib import Path
from typing import Any

from playquick.models import PlaybackState, PlaybackStatus, RepeatMode, Track
from playquick.playback.transport import (
    MpvTransport,
    UnixSocketTransport,
    WindowsNamedPipeTransport,
)


class MpvError(RuntimeError):
    pass


class MpvController:
    def __init__(self, executable: Path, transport: MpvTransport | None = None) -> None:
        self.executable = executable
        self._transport = transport
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self._request_lock = asyncio.Lock()
        self._state = PlaybackState()
        self._states: asyncio.Queue[PlaybackState] = asyncio.Queue()
        self._ipc_address = self._new_ipc_address()

    @property
    def state(self) -> PlaybackState:
        return self._state

    def _new_ipc_address(self) -> str:
        token = uuid.uuid4().hex
        if os.name == "nt":
            return rf"\\.\pipe\playquick-{token}"
        return str(Path(tempfile.gettempdir()) / f"playquick-{token}.sock")

    async def start(self) -> None:
        if self._transport is None:
            if os.name == "nt":
                self._transport = WindowsNamedPipeTransport(self._ipc_address)
            else:
                self._transport = UnixSocketTransport(Path(self._ipc_address))
            self._process = await asyncio.create_subprocess_exec(
                str(self.executable),
                "--idle=yes",
                "--no-video",
                "--no-terminal",
                f"--input-ipc-server={self._ipc_address}",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await self._connect_with_retry()
        else:
            await self._transport.connect()
        await self.set_volume(self._state.volume)

    async def _connect_with_retry(self) -> None:
        assert self._transport is not None
        for _ in range(50):
            if self._process and self._process.returncode is not None:
                raise MpvError(f"mpv exited with code {self._process.returncode}")
            try:
                await self._transport.connect()
                return
            except (FileNotFoundError, ConnectionError, OSError):
                await asyncio.sleep(0.1)
        raise MpvError("Timed out connecting to mpv IPC")

    async def close(self) -> None:
        if self._transport:
            with suppress(ConnectionError, MpvError):
                await self._command("quit")
            await self._transport.close()
        if self._process:
            try:
                await asyncio.wait_for(self._process.wait(), timeout=2)
            except TimeoutError:
                self._process.terminate()
                await self._process.wait()
        if os.name != "nt":
            Path(self._ipc_address).unlink(missing_ok=True)

    async def _command(self, *command: object) -> Any:
        if not self._transport:
            raise ConnectionError("mpv is not started")
        async with self._request_lock:
            self._request_id += 1
            request_id = self._request_id
            payload = json.dumps({"command": command, "request_id": request_id}).encode()
            await self._transport.send_line(payload)
            while True:
                response: dict[str, Any] = json.loads(await self._transport.read_line())
                if response.get("request_id") != request_id:
                    continue
                if response.get("error") != "success":
                    raise MpvError(str(response.get("error", "unknown mpv error")))
                return response.get("data")

    async def play(self, track: Track) -> None:
        await self._command("loadfile", str(track.path), "replace")
        self._state.track = track
        self._state.status = PlaybackStatus.PLAYING
        self._state.position = 0
        self._state.duration = track.duration
        self._emit()

    async def pause(self, paused: bool | None = None) -> None:
        target = self._state.status == PlaybackStatus.PLAYING if paused is None else paused
        await self._command("set_property", "pause", target)
        self._state.status = PlaybackStatus.PAUSED if target else PlaybackStatus.PLAYING
        self._emit()

    async def stop(self) -> None:
        await self._command("stop")
        self._state.status = PlaybackStatus.STOPPED
        self._state.position = 0
        self._emit()

    async def seek(self, seconds: float) -> None:
        await self._command("seek", seconds, "relative", "exact")
        self._state.position = max(0, self._state.position + seconds)
        self._emit()

    async def set_volume(self, volume: int) -> None:
        volume = max(0, min(100, volume))
        await self._command("set_property", "volume", volume)
        self._state.volume = volume
        self._emit()

    async def next(self) -> None:
        await self._command("playlist-next", "force")

    async def previous(self) -> None:
        await self._command("playlist-prev", "force")

    async def set_shuffle(self, enabled: bool) -> None:
        self._state.shuffle = enabled
        self._emit()

    async def set_repeat(self, mode: RepeatMode) -> None:
        value: str | int = "inf" if mode == RepeatMode.ALL else 0
        await self._command("set_property", "loop-playlist", value)
        await self._command("set_property", "loop-file", "inf" if mode == RepeatMode.ONE else 0)
        self._state.repeat = mode
        self._emit()

    async def poll(self) -> PlaybackState:
        position = await self._command("get_property", "time-pos")
        duration = await self._command("get_property", "duration")
        paused = await self._command("get_property", "pause")
        self._state.position = float(position or 0)
        self._state.duration = float(duration or self._state.duration)
        if self._state.track:
            self._state.status = PlaybackStatus.PAUSED if paused else PlaybackStatus.PLAYING
        self._emit()
        return self._state

    def _emit(self) -> None:
        self._states.put_nowait(self._state)

    async def states(self) -> AsyncIterator[PlaybackState]:
        while True:
            yield await self._states.get()
