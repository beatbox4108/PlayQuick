from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from pathlib import Path

from watchfiles import awatch


async def watch_library(
    roots: Iterable[Path], on_change: Callable[[set[Path]], Awaitable[None]]
) -> None:
    resolved = [root.resolve() for root in roots if root.is_dir()]
    if not resolved:
        return
    async for changes in awatch(*resolved):
        paths = {Path(changed).resolve() for _, changed in changes}
        await on_change(paths)

