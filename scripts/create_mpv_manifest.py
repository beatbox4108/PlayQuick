from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def main(directory: Path, repository: str, tag: str) -> None:
    assets = []
    for path in sorted(directory.glob("mpv-*")):
        if not path.is_file() or path.name.endswith("manifest.json"):
            continue
        parts = path.name.split("-")
        if len(parts) < 3 or parts[1] not in {"linux", "windows"}:
            continue
        system = parts[1]
        arch = parts[2].split(".")[0]
        archive = "zip" if path.suffix == ".zip" else "tar.gz"
        assets.append(
            {
                "platform": system,
                "arch": arch,
                "url": f"https://github.com/{repository}/releases/download/{tag}/{path.name}",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size": path.stat().st_size,
                "archive": archive,
                "executable": "mpv.exe" if system == "windows" else "mpv",
            }
        )
    manifest = {
        "mpv_version": "0.41.0",
        "license": "GPL-2.0-or-later",
        "source_url": "https://github.com/mpv-player/mpv/archive/refs/tags/v0.41.0.tar.gz",
        "assets": assets,
    }
    (directory / "mpv-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2], sys.argv[3])
