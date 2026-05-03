from __future__ import annotations
import os
import tomllib
import tomli_w
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rtxcopy.destinations import Destination

from rtxcopy.destinations import destination_from_dict, destination_to_dict


def get_config_dir() -> Path:
    d = Path("~/.config/rtxtools/rtxcopy").expanduser()
    d.mkdir(parents=True, exist_ok=True)
    d.chmod(0o700)
    (d / "keys").mkdir(exist_ok=True)
    (d / "keys").chmod(0o700)
    return d


@dataclass
class Config:
    destinations: list[Destination] = field(default_factory=list)
    default_local_start_path: str = "~"
    # favorites: {"dest_name": ["/path/a", "/path/b"]}
    favorites: dict[str, list[str]] = field(default_factory=dict)

    def get_favorites(self, dest_name: str) -> list[str]:
        return self.favorites.get(dest_name, [])

    def add_favorite(self, dest_name: str, path: str) -> None:
        favs = self.favorites.setdefault(dest_name, [])
        if path not in favs:
            favs.append(path)

    def remove_favorite(self, dest_name: str, path: str) -> None:
        if dest_name in self.favorites:
            self.favorites[dest_name] = [p for p in self.favorites[dest_name] if p != path]

    def is_favorite(self, dest_name: str, path: str) -> bool:
        return path in self.favorites.get(dest_name, [])


def load_config() -> Config:
    config_file = get_config_dir() / "config.toml"
    if not config_file.exists():
        return Config()
    with open(config_file, "rb") as f:
        data = tomllib.load(f)
    settings = data.get("settings", {})
    destinations = [destination_from_dict(d) for d in data.get("destinations", [])]
    favorites = data.get("favorites", {})
    return Config(
        destinations=destinations,
        default_local_start_path=settings.get("default_local_start_path", "~"),
        favorites=favorites,
    )


def save_config(config: Config) -> None:
    config_file = get_config_dir() / "config.toml"
    data: dict = {
        "settings": {
            "default_local_start_path": config.default_local_start_path,
        },
        "destinations": [destination_to_dict(d) for d in config.destinations],
    }
    if config.favorites:
        data["favorites"] = config.favorites
    tmp = config_file.with_suffix(".toml.tmp")
    with open(tmp, "wb") as f:
        tomli_w.dump(data, f)
    tmp.replace(config_file)
