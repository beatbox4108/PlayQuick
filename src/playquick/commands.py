from __future__ import annotations

from collections.abc import Sequence


def scan_paths(paths: Sequence[str]) -> int:
    for path in paths:
        print(f"Scan support will index: {path}")
    return 0

