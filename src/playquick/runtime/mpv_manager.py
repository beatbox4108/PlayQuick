from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import httpx
from platformdirs import user_data_path

MPV_VERSION = "0.41.0"
MANIFEST_URL = (
    "https://github.com/beatbox4108/PlayQuick/releases/download/"
    "mpv-v0.41.0-pq1/mpv-manifest.json"
)


@dataclass(slots=True, frozen=True)
class MpvAsset:
    platform: str
    arch: str
    url: str
    sha256: str
    size: int
    archive: str
    executable: str

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> MpvAsset:
        return cls(
            platform=str(value["platform"]),
            arch=str(value["arch"]),
            url=str(value["url"]),
            sha256=str(value["sha256"]),
            size=int(value["size"]),
            archive=str(value["archive"]),
            executable=str(value["executable"]),
        )


def platform_key() -> tuple[str, str]:
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = {
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }.get(machine, machine)
    return system, arch


class MpvRuntimeManager:
    def __init__(
        self,
        *,
        configured_path: Path | None = None,
        data_dir: Path | None = None,
        manifest_url: str = MANIFEST_URL,
        client: httpx.Client | None = None,
    ) -> None:
        self.configured_path = configured_path
        self.data_dir = data_dir or user_data_path("PlayQuick") / "runtime" / "mpv"
        self.manifest_url = manifest_url
        self.client = client or httpx.Client(follow_redirects=True, timeout=60)

    @property
    def managed_executable(self) -> Path:
        executable = "mpv.exe" if os.name == "nt" else "mpv"
        system, arch = platform_key()
        return self.data_dir / MPV_VERSION / f"{system}-{arch}" / executable

    def resolve(self) -> Path | None:
        if self.configured_path and self.configured_path.is_file():
            return self.configured_path
        system = shutil.which("mpv")
        if system:
            return Path(system)
        if self.managed_executable.is_file():
            return self.managed_executable
        return None

    def install(self, *, repair: bool = False, verify: bool = True) -> Path:
        manifest_response = self.client.get(self.manifest_url)
        manifest_response.raise_for_status()
        manifest = manifest_response.json()
        system, arch = platform_key()
        assets = [MpvAsset.from_mapping(value) for value in manifest.get("assets", [])]
        asset = next(
            (item for item in assets if item.platform == system and item.arch == arch), None
        )
        if asset is None:
            raise RuntimeError(f"No managed mpv build for {system}/{arch}")
        if not asset.url.startswith("https://"):
            raise RuntimeError("Managed mpv asset URL must use HTTPS")
        target = self.data_dir / MPV_VERSION / f"{system}-{arch}"
        executable = target / asset.executable
        if executable.is_file() and not repair:
            return executable
        response = self.client.get(asset.url)
        response.raise_for_status()
        payload = response.content
        if len(payload) != asset.size:
            raise RuntimeError("Managed mpv download size mismatch")
        digest = hashlib.sha256(payload).hexdigest()
        if digest.lower() != asset.sha256.lower():
            raise RuntimeError("Managed mpv checksum mismatch")
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=target.parent) as temporary_name:
            temporary = Path(temporary_name)
            archive = temporary / f"mpv.{asset.archive}"
            archive.write_bytes(payload)
            extracted = temporary / "extracted"
            extracted.mkdir()
            self._extract(archive, extracted, asset.archive)
            staged = temporary / "staged"
            shutil.copytree(extracted, staged)
            if target.exists():
                shutil.rmtree(target)
            staged.replace(target)
        if not executable.is_file():
            raise RuntimeError(f"Managed mpv archive did not contain {asset.executable}")
        if os.name != "nt":
            executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
        if verify:
            self.verify(executable)
        return executable

    @staticmethod
    def verify(executable: Path) -> str:
        result = subprocess.run(
            [str(executable), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or f"exit code {result.returncode}"
            raise RuntimeError(f"Managed mpv failed its startup check: {detail}")
        return result.stdout.splitlines()[0] if result.stdout else "mpv"

    @staticmethod
    def _safe_destination(root: Path, member: str) -> Path:
        normalized = PurePosixPath(member.replace("\\", "/"))
        if normalized.is_absolute() or ".." in normalized.parts:
            raise RuntimeError(f"Unsafe archive member: {member}")
        destination = root.joinpath(*normalized.parts).resolve()
        if not destination.is_relative_to(root.resolve()):
            raise RuntimeError(f"Unsafe archive member: {member}")
        return destination

    def _extract(self, archive: Path, destination: Path, kind: str) -> None:
        if kind == "zip":
            with zipfile.ZipFile(archive) as bundle:
                for member in bundle.infolist():
                    self._safe_destination(destination, member.filename)
                bundle.extractall(destination)
            return
        if kind in {"tar.gz", "tgz"}:
            with tarfile.open(archive, "r:gz") as bundle:
                for tar_member in bundle.getmembers():
                    self._safe_destination(destination, tar_member.name)
                bundle.extractall(destination, filter="data")
            return
        raise RuntimeError(f"Unsupported managed mpv archive: {kind}")


def format_manifest(assets: list[MpvAsset]) -> bytes:
    return json.dumps(
        {
            "mpv_version": MPV_VERSION,
            "license": "GPL-2.0-or-later",
            "source_url": f"https://github.com/mpv-player/mpv/archive/refs/tags/v{MPV_VERSION}.tar.gz",
            "assets": [
                {
                    "platform": asset.platform,
                    "arch": asset.arch,
                    "url": asset.url,
                    "sha256": asset.sha256,
                    "size": asset.size,
                    "archive": asset.archive,
                    "executable": asset.executable,
                }
                for asset in assets
            ],
        },
        indent=2,
    ).encode()
