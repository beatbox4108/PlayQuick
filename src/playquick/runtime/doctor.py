from __future__ import annotations

import platform
import shutil


def run_doctor() -> int:
    mpv = shutil.which("mpv")
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"mpv: {mpv or 'not found'}")
    return 0 if mpv else 1

