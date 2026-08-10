from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, BinaryIO, Protocol


class MpvTransport(Protocol):
    async def connect(self) -> None: ...
    async def close(self) -> None: ...
    async def send_line(self, data: bytes) -> None: ...
    async def read_line(self) -> bytes: ...


class UnixSocketTransport:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def connect(self) -> None:
        open_connection: Any = asyncio.open_unix_connection  # type: ignore[attr-defined,unused-ignore]
        self._reader, self._writer = await open_connection(str(self.path))

    async def close(self) -> None:
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

    async def send_line(self, data: bytes) -> None:
        if not self._writer:
            raise ConnectionError("mpv IPC is not connected")
        self._writer.write(data + b"\n")
        await self._writer.drain()

    async def read_line(self) -> bytes:
        if not self._reader:
            raise ConnectionError("mpv IPC is not connected")
        line = await self._reader.readline()
        if not line:
            raise ConnectionError("mpv IPC closed")
        return line


class WindowsNamedPipeTransport:
    def __init__(self, pipe_name: str) -> None:
        self.pipe_name = pipe_name
        self._pipe: BinaryIO | None = None

    async def connect(self) -> None:
        self._pipe = await asyncio.to_thread(open, self.pipe_name, "r+b", buffering=0)

    async def close(self) -> None:
        pipe, self._pipe = self._pipe, None
        if pipe:
            await asyncio.to_thread(pipe.close)

    async def send_line(self, data: bytes) -> None:
        if not self._pipe:
            raise ConnectionError("mpv IPC is not connected")
        await asyncio.to_thread(self._pipe.write, data + b"\n")

    async def read_line(self) -> bytes:
        if not self._pipe:
            raise ConnectionError("mpv IPC is not connected")
        line = await asyncio.to_thread(self._pipe.readline)
        if not line:
            raise ConnectionError("mpv IPC closed")
        return line
