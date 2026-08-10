from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import tomli_w
from platformdirs import user_config_path, user_data_path


@dataclass(slots=True)
class AppConfig:
    music_dirs: list[str] = field(default_factory=list)
    mpv_path: str | None = None
    theme: str = "dark"
    volume: int = 70
    spotify_client_id: str | None = None
    spotify_extended_library: bool = False

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> AppConfig:
        allowed = {key: value[key] for key in cls.__dataclass_fields__ if key in value}
        return cls(**allowed)


class ConfigStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or user_config_path("PlayQuick") / "config.toml"

    def load(self) -> AppConfig:
        if not self.path.exists():
            return AppConfig()
        with self.path.open("rb") as stream:
            value = tomllib.load(stream)
        return AppConfig.from_mapping(value)

    def save(self, config: AppConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        values = {key: value for key, value in asdict(config).items() if value is not None}
        temporary.write_bytes(tomli_w.dumps(values).encode("utf-8"))
        temporary.replace(self.path)


def default_database_path() -> Path:
    return user_data_path("PlayQuick") / "library.db"
