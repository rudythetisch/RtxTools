from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Union


@dataclass
class NASDestination:
    type: Literal["nas"]
    name: str
    host: str
    username: str
    ssh_key_path: str
    port: int = 22
    default_remote_path: str = "/"

    @property
    def key_path(self) -> Path:
        return Path(self.ssh_key_path).expanduser()


@dataclass
class ProxmoxLXCDestination:
    type: Literal["proxmox_lxc"]
    name: str
    node_host: str
    node_username: str
    ssh_key_path: str
    vmid: int
    node_port: int = 22
    default_remote_path: str = "/root"

    @property
    def key_path(self) -> Path:
        return Path(self.ssh_key_path).expanduser()


@dataclass
class ProxmoxQEMUDestination:
    type: Literal["proxmox_qemu"]
    name: str
    node_host: str
    node_username: str
    ssh_key_path: str
    vmid: int
    node_port: int = 22
    default_remote_path: str = "/root"

    @property
    def key_path(self) -> Path:
        return Path(self.ssh_key_path).expanduser()


Destination = Union[NASDestination, ProxmoxLXCDestination, ProxmoxQEMUDestination]

_DEST_CLASSES = {
    "nas": NASDestination,
    "proxmox_lxc": ProxmoxLXCDestination,
    "proxmox_qemu": ProxmoxQEMUDestination,
}


def destination_from_dict(d: dict) -> Destination:
    dest_type = d.get("type")
    cls = _DEST_CLASSES.get(dest_type)
    if cls is None:
        raise ValueError(f"Unknown destination type: {dest_type!r}")
    return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def destination_to_dict(dest: Destination) -> dict:
    import dataclasses
    return dataclasses.asdict(dest)
