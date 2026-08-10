from __future__ import annotations

import platform
from pathlib import Path

from playquick.config import ConfigStore
from playquick.runtime.mpv_manager import MpvRuntimeManager


def run_doctor(*, install: bool = False, repair: bool = False) -> int:
    config = ConfigStore().load()
    configured = Path(config.mpv_path) if config.mpv_path else None
    manager = MpvRuntimeManager(configured_path=configured)
    mpv = manager.install(repair=repair) if install or repair else manager.resolve()
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"mpv: {mpv or 'not found'}")
    if not mpv:
        return 1
    try:
        print(f"mpv version: {manager.verify(mpv)}")
    except (OSError, RuntimeError) as error:
        print(f"mpv check failed: {error}")
        return 2
    return 0
