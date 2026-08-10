from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import httpx
import pytest

from playquick.runtime.mpv_manager import MpvRuntimeManager, platform_key


def zip_payload(name: str = "mpv.exe") -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(name, b"executable")
    return output.getvalue()


def test_installs_verified_asset(tmp_path: Path) -> None:
    system, arch = platform_key()
    executable = "mpv.exe" if system == "windows" else "mpv"
    payload = zip_payload(executable)
    manifest = {
        "assets": [
            {
                "platform": system,
                "arch": arch,
                "url": "https://example.test/mpv.zip",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size": len(payload),
                "archive": "zip",
                "executable": executable,
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("manifest.json"):
            return httpx.Response(200, json=manifest)
        return httpx.Response(200, content=payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    manager = MpvRuntimeManager(
        data_dir=tmp_path, manifest_url="https://example.test/manifest.json", client=client
    )
    assert manager.install().read_bytes() == b"executable"


def test_rejects_checksum_mismatch(tmp_path: Path) -> None:
    system, arch = platform_key()
    payload = zip_payload()
    manifest = {
        "assets": [
            {
                "platform": system,
                "arch": arch,
                "url": "https://example.test/mpv.zip",
                "sha256": "0" * 64,
                "size": len(payload),
                "archive": "zip",
                "executable": "mpv.exe",
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if "manifest" in str(request.url):
            return httpx.Response(200, json=manifest)
        return httpx.Response(200, content=payload)

    manager = MpvRuntimeManager(
        data_dir=tmp_path,
        manifest_url="https://example.test/manifest.json",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(RuntimeError, match="checksum"):
        manager.install()


def test_rejects_path_traversal(tmp_path: Path) -> None:
    manager = MpvRuntimeManager(data_dir=tmp_path)
    with pytest.raises(RuntimeError, match="Unsafe"):
        manager._safe_destination(tmp_path, "../escape")
